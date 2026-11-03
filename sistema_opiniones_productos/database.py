from contextlib import contextmanager
from typing import Any, Iterator

import mysql.connector
from flask import current_app
from mysql.connector.connection import MySQLConnection


class RelatedRecordsError(Exception):
    """Raised when a product is still referenced by comments."""


@contextmanager
def connection_scope() -> Iterator[MySQLConnection]:
    connection = mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        port=current_app.config["DB_PORT"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        database=current_app.config["DB_NAME"],
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        autocommit=False,
    )
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _read_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection_scope() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()


def _read_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connection_scope() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()


def get_products() -> list[dict[str, Any]]:
    return _read_all(
        """
        SELECT id_producto, nombre, descripcion, categoria, fecha_registro
        FROM productos
        ORDER BY nombre
        """
    )


def get_product(product_id: int) -> dict[str, Any] | None:
    return _read_one(
        """
        SELECT id_producto, nombre, descripcion, categoria, fecha_registro
        FROM productos
        WHERE id_producto = %s
        """,
        (product_id,),
    )


def save_product(
    name: str, description: str, category: str, product_id: int | None = None
) -> None:
    with connection_scope() as connection:
        cursor = connection.cursor()
        try:
            if product_id is None:
                cursor.execute(
                    """
                    INSERT INTO productos (nombre, descripcion, categoria)
                    VALUES (%s, %s, %s)
                    """,
                    (name, description, category),
                )
            else:
                cursor.execute(
                    """
                    UPDATE productos
                    SET nombre = %s, descripcion = %s, categoria = %s
                    WHERE id_producto = %s
                    """,
                    (name, description, category, product_id),
                )
        finally:
            cursor.close()


def delete_product(product_id: int) -> None:
    with connection_scope() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM comentarios_productos WHERE id_producto = %s",
                (product_id,),
            )
            if cursor.fetchone()[0]:
                raise RelatedRecordsError(
                    "No se puede eliminar el producto porque tiene comentarios asociados."
                )
            cursor.execute("DELETE FROM productos WHERE id_producto = %s", (product_id,))
        finally:
            cursor.close()


def get_clients() -> list[dict[str, Any]]:
    return _read_all(
        """
        SELECT c.id_cliente, c.nombre, c.correo, c.fecha_registro,
               COUNT(cp.id_comentario) AS total_comentarios
        FROM clientes AS c
        LEFT JOIN comentarios_productos AS cp ON cp.id_cliente = c.id_cliente
        GROUP BY c.id_cliente, c.nombre, c.correo, c.fecha_registro
        ORDER BY c.nombre
        """
    )


def create_comment(
    product_id: int,
    client_name: str,
    client_email: str,
    comment: str,
    likes_product: bool,
) -> int:
    with connection_scope() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO clientes (nombre, correo)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE id_cliente = LAST_INSERT_ID(id_cliente)
                """,
                (client_name, client_email),
            )
            client_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO comentarios_productos
                    (id_producto, id_cliente, comentario, like_producto, dislike_producto)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    product_id,
                    client_id,
                    comment,
                    likes_product,
                    not likes_product,
                ),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


def get_comments(
    search: str = "", product_id: int | None = None, sentiment: str = ""
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if search:
        conditions.append(
            "(cp.comentario LIKE %s OR c.nombre LIKE %s OR p.nombre LIKE %s)"
        )
        pattern = f"%{search}%"
        params.extend((pattern, pattern, pattern))
    if product_id is not None:
        conditions.append("cp.id_producto = %s")
        params.append(product_id)
    if sentiment:
        conditions.append("a.sentimiento = %s")
        params.append(sentiment)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return _read_all(
        f"""
        SELECT cp.id_comentario, cp.comentario, cp.like_producto, cp.dislike_producto,
               cp.fecha_comentario, p.id_producto, p.nombre AS producto,
               c.nombre AS cliente, c.correo, a.sentimiento, a.puntuacion
        FROM comentarios_productos AS cp
        JOIN productos AS p ON p.id_producto = cp.id_producto
        JOIN clientes AS c ON c.id_cliente = cp.id_cliente
        LEFT JOIN analisis_comentarios AS a ON a.id_comentario = cp.id_comentario
        {where_clause}
        ORDER BY cp.fecha_comentario DESC, cp.id_comentario DESC
        """,
        tuple(params),
    )


def get_comment(comment_id: int) -> dict[str, Any] | None:
    return _read_one(
        """
        SELECT cp.id_comentario, cp.comentario, cp.like_producto, cp.dislike_producto,
               cp.fecha_comentario, p.nombre AS producto, c.nombre AS cliente,
               c.correo, a.sentimiento, a.puntuacion, a.palabras_clave,
               a.fecha_analisis
        FROM comentarios_productos AS cp
        JOIN productos AS p ON p.id_producto = cp.id_producto
        JOIN clientes AS c ON c.id_cliente = cp.id_cliente
        LEFT JOIN analisis_comentarios AS a ON a.id_comentario = cp.id_comentario
        WHERE cp.id_comentario = %s
        """,
        (comment_id,),
    )


def get_comment_for_analysis(comment_id: int) -> dict[str, Any] | None:
    return _read_one(
        """
        SELECT cp.id_comentario, cp.comentario, a.id_analisis
        FROM comentarios_productos AS cp
        LEFT JOIN analisis_comentarios AS a ON a.id_comentario = cp.id_comentario
        WHERE cp.id_comentario = %s
        """,
        (comment_id,),
    )


def save_analysis(
    comment_id: int, sentiment: str, confidence: float, keywords: str
) -> None:
    with connection_scope() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO analisis_comentarios
                    (id_comentario, sentimiento, puntuacion, palabras_clave)
                VALUES (%s, %s, %s, %s)
                """,
                (comment_id, sentiment, confidence, keywords),
            )
        finally:
            cursor.close()


def get_pending_comment_ids() -> list[int]:
    rows = _read_all(
        """
        SELECT cp.id_comentario
        FROM comentarios_productos AS cp
        LEFT JOIN analisis_comentarios AS a ON a.id_comentario = cp.id_comentario
        WHERE a.id_analisis IS NULL
        ORDER BY cp.id_comentario
        """
    )
    return [row["id_comentario"] for row in rows]


def get_dashboard_stats() -> dict[str, int]:
    row = _read_one(
        """
        SELECT
            (SELECT COUNT(*) FROM productos) AS productos,
            (SELECT COUNT(*) FROM clientes) AS clientes,
            (SELECT COUNT(*) FROM comentarios_productos) AS comentarios,
            (SELECT COUNT(*) FROM comentarios_productos WHERE like_producto = 1) AS likes,
            (SELECT COUNT(*) FROM comentarios_productos WHERE dislike_producto = 1) AS dislikes,
            (SELECT COUNT(*) FROM analisis_comentarios WHERE sentimiento = 'POSITIVO') AS positivos,
            (SELECT COUNT(*) FROM analisis_comentarios WHERE sentimiento = 'NEGATIVO') AS negativos,
            (SELECT COUNT(*) FROM analisis_comentarios WHERE sentimiento = 'NEUTRAL') AS neutrales
        """
    )
    return row or {}


def get_recent_comments(limit: int = 5) -> list[dict[str, Any]]:
    return _read_all(
        """
        SELECT cp.id_comentario, cp.comentario, cp.fecha_comentario,
               p.nombre AS producto, c.nombre AS cliente, a.sentimiento
        FROM comentarios_productos AS cp
        JOIN productos AS p ON p.id_producto = cp.id_producto
        JOIN clientes AS c ON c.id_cliente = cp.id_cliente
        LEFT JOIN analisis_comentarios AS a ON a.id_comentario = cp.id_comentario
        ORDER BY cp.fecha_comentario DESC, cp.id_comentario DESC
        LIMIT %s
        """,
        (limit,),
    )
