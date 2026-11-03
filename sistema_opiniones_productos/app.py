import logging
import os
from functools import wraps
from typing import Any, Callable, TypeVar

import mysql.connector
from email_validator import EmailNotValidError, validate_email
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

import database
from config import Config
from sentiment_analysis import (
    SentimentAnalysisError,
    analyze_comment,
    analyze_pending_comments,
)

logging.basicConfig(level=logging.INFO)
csrf = CSRFProtect()
F = TypeVar("F", bound=Callable[..., Any])


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Configura SECRET_KEY en el archivo .env antes de iniciar.")
    csrf.init_app(app)

    def database_errors(view: F) -> F:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return view(*args, **kwargs)
            except mysql.connector.Error:
                app.logger.exception("Error al consultar MySQL.")
                return render_template("error.html"), 503

        return wrapped  # type: ignore[return-value]

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError) -> tuple[str, int]:
        return render_template("error.html", message="El formulario expiró. Recarga la página e inténtalo nuevamente."), 400

    @app.errorhandler(404)
    def not_found(_: Any) -> tuple[str, int]:
        return render_template("error.html", message="No se encontró la página solicitada."), 404

    @app.errorhandler(500)
    def internal_error(_: Any) -> tuple[str, int]:
        app.logger.exception("Error interno de la aplicación.")
        return render_template("error.html"), 500

    @app.get("/")
    @database_errors
    def index() -> str:
        return render_template(
            "index.html",
            stats=database.get_dashboard_stats(),
            recent_comments=database.get_recent_comments(5),
        )

    @app.get("/dashboard")
    @database_errors
    def dashboard() -> str:
        stats = database.get_dashboard_stats()
        total_analyzed = stats["positivos"] + stats["negativos"] + stats["neutrales"]
        return render_template(
            "dashboard.html",
            stats=stats,
            total_analyzed=total_analyzed,
        )

    @app.route("/productos", methods=["GET", "POST"])
    @database_errors
    def products() -> Any:
        if request.method == "POST":
            name = request.form.get("nombre", "").strip()
            description = request.form.get("descripcion", "").strip()
            category = request.form.get("categoria", "").strip()
            if not name or len(name) > 150 or len(category) > 100:
                flash("Indica un nombre válido (máximo 150 caracteres) y una categoría de hasta 100 caracteres.", "error")
            else:
                database.save_product(name, description, category)
                flash("Producto registrado correctamente.", "success")
                return redirect(url_for("products"))
        return render_template("products.html", products=database.get_products())

    @app.route("/productos/<int:product_id>/editar", methods=["GET", "POST"])
    @database_errors
    def edit_product(product_id: int) -> Any:
        product = database.get_product(product_id)
        if product is None:
            return render_template("error.html", message="No se encontró el producto."), 404
        if request.method == "POST":
            name = request.form.get("nombre", "").strip()
            description = request.form.get("descripcion", "").strip()
            category = request.form.get("categoria", "").strip()
            if not name or len(name) > 150 or len(category) > 100:
                flash("Indica un nombre válido (máximo 150 caracteres) y una categoría de hasta 100 caracteres.", "error")
            else:
                database.save_product(name, description, category, product_id)
                flash("Producto actualizado correctamente.", "success")
                return redirect(url_for("products"))
        return render_template("product_form.html", product=product)

    @app.post("/productos/<int:product_id>/eliminar")
    @database_errors
    def remove_product(product_id: int) -> Any:
        try:
            database.delete_product(product_id)
            flash("Producto eliminado.", "success")
        except database.RelatedRecordsError as error:
            flash(str(error), "error")
        return redirect(url_for("products"))

    @app.get("/clientes")
    @database_errors
    def clients() -> str:
        return render_template("clients.html", clients=database.get_clients())

    @app.get("/comentarios")
    @database_errors
    def comments() -> str:
        search = request.args.get("q", "").strip()[:150]
        selected_product = request.args.get("producto", "").strip()
        product_id: int | None = None
        if selected_product:
            try:
                product_id = int(selected_product)
            except ValueError:
                flash("El filtro de producto no es válido.", "error")
        sentiment = request.args.get("sentimiento", "").upper()
        if sentiment not in {"", "POSITIVO", "NEGATIVO", "NEUTRAL"}:
            flash("El filtro de sentimiento no es válido.", "error")
            sentiment = ""
        return render_template(
            "comments.html",
            comments=database.get_comments(search, product_id, sentiment),
            products=database.get_products(),
            search=search,
            selected_product=selected_product,
            selected_sentiment=sentiment,
        )

    @app.route("/comentarios/nuevo", methods=["GET", "POST"])
    @database_errors
    def new_comment() -> Any:
        products_list = database.get_products()
        if request.method == "POST":
            product_value = request.form.get("id_producto", "")
            client_name = request.form.get("nombre", "").strip()
            client_email = request.form.get("correo", "").strip()
            comment_text = request.form.get("comentario", "").strip()
            vote = request.form.get("opinion", "")
            errors: list[str] = []
            try:
                product_id = int(product_value)
            except ValueError:
                product_id = 0
            if not any(item["id_producto"] == product_id for item in products_list):
                errors.append("Selecciona un producto existente.")
            if not client_name or len(client_name) > 150:
                errors.append("El nombre es obligatorio y no puede superar 150 caracteres.")
            if len(client_email) > 150:
                errors.append("El correo no puede superar 150 caracteres.")
            else:
                try:
                    client_email = validate_email(client_email, check_deliverability=False).normalized
                except EmailNotValidError:
                    errors.append("Ingresa un correo electrónico válido.")
            if not comment_text or len(comment_text) > 5000:
                errors.append("El comentario es obligatorio y no puede superar 5000 caracteres.")
            if vote not in {"like", "dislike"}:
                errors.append("Selecciona Like o Dislike.")
            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                comment_id = database.create_comment(
                    product_id,
                    client_name,
                    client_email,
                    comment_text,
                    vote == "like",
                )
                flash("Comentario guardado correctamente.", "success")
                return redirect(url_for("comment_detail", comment_id=comment_id))
        return render_template("new_comment.html", products=products_list)

    @app.get("/comentarios/<int:comment_id>")
    @database_errors
    def comment_detail(comment_id: int) -> Any:
        comment = database.get_comment(comment_id)
        if comment is None:
            return render_template("error.html", message="No se encontró el comentario."), 404
        return render_template("comment_detail.html", comment=comment)

    @app.get("/analisis")
    @database_errors
    def analysis() -> str:
        sentiment = request.args.get("sentimiento", "").upper()
        if sentiment not in {"", "POSITIVO", "NEGATIVO", "NEUTRAL"}:
            flash("El filtro de sentimiento no es válido.", "error")
            sentiment = ""
        return render_template(
            "analysis.html",
            comments=database.get_comments(sentiment=sentiment),
            selected_sentiment=sentiment,
        )

    @app.post("/analisis/pendientes")
    @database_errors
    def analyze_pending() -> Any:
        analyzed, errors = analyze_pending_comments()
        if analyzed:
            flash(f"Se analizaron {analyzed} comentario(s).", "success")
        if errors:
            flash(" ".join(errors[:3]), "error")
        if not analyzed and not errors:
            flash("No hay comentarios pendientes de análisis.", "info")
        return redirect(url_for("analysis"))

    @app.post("/analisis/<int:comment_id>")
    @database_errors
    def analyze_one(comment_id: int) -> Any:
        try:
            result = analyze_comment(comment_id)
            if result is None:
                flash("Este comentario ya tiene un análisis; no se volvió a procesar.", "info")
            else:
                flash("Análisis guardado correctamente.", "success")
        except SentimentAnalysisError as error:
            flash(str(error), "error")
        return redirect(url_for("analysis_detail", comment_id=comment_id))

    @app.get("/analisis/<int:comment_id>")
    @database_errors
    def analysis_detail(comment_id: int) -> Any:
        comment = database.get_comment(comment_id)
        if comment is None:
            return render_template("error.html", message="No se encontró el comentario."), 404
        return render_template("analysis_detail.html", comment=comment)

    @app.cli.command("check-db")
    def check_db() -> None:
        with database.connection_scope() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT VERSION()")
                print(f"Conexión MySQL correcta. Versión: {cursor.fetchone()[0]}")
            finally:
                cursor.close()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=app.config["DEBUG"],
    )
