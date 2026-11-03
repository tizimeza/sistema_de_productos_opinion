import logging
import re
import threading
from collections import Counter
from typing import Any

import database

logger = logging.getLogger(__name__)
_analyzer: Any = None
_analyzer_lock = threading.Lock()

_SPANISH_STOP_WORDS = {
    "a", "al", "algo", "algunas", "algunos", "ante", "como", "con", "cual",
    "cuando", "de", "del", "desde", "donde", "el", "ella", "ellas", "ellos",
    "en", "entre", "era", "es", "esa", "ese", "eso", "esta", "está", "este",
    "esto", "fue", "ha", "hasta", "hay", "la", "las", "le", "les", "lo",
    "los", "más", "me", "mi", "mis", "muy", "no", "nos", "o", "para", "pero",
    "por", "que", "qué", "se", "sin", "su", "sus", "un", "una", "uno", "unos",
    "y", "ya",
}


class SentimentAnalysisError(Exception):
    """Raised when sentiment analysis cannot produce a genuine model result."""


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_keywords(text: str, limit: int = 8) -> str:
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", text.lower())
    keywords = [word for word, _ in Counter(
        word for word in words if word not in _SPANISH_STOP_WORDS
    ).most_common(limit)]
    return ", ".join(keywords)


def _get_analyzer() -> Any:
    global _analyzer
    if _analyzer is not None:
        return _analyzer
    with _analyzer_lock:
        if _analyzer is not None:
            return _analyzer
        try:
            from pysentimiento import create_analyzer

            _analyzer = create_analyzer(task="sentiment", lang="es")
        except Exception as error:
            logger.exception("No se pudo cargar el modelo de PySentimiento.")
            raise SentimentAnalysisError(
                "No fue posible cargar el modelo de sentimientos. "
                "Comprueba la instalación y la conexión a Internet del primer uso."
            ) from error
    return _analyzer


def _predict(text: str) -> tuple[str, float, str]:
    cleaned = clean_text(text)
    if not cleaned:
        raise SentimentAnalysisError("El comentario no contiene texto para analizar.")
    analyzer = _get_analyzer()
    try:
        result = analyzer.predict(cleaned)
        model_label = str(result.output).upper()
        label_map = {"POS": "POSITIVO", "NEG": "NEGATIVO", "NEU": "NEUTRAL"}
        if model_label not in label_map:
            raise ValueError(f"Etiqueta de sentimiento inesperada: {model_label}")
        confidence = float(result.probas[model_label])
        if not 0 <= confidence <= 1:
            raise ValueError("El modelo devolvió una probabilidad fuera de rango.")
    except Exception as error:
        logger.exception("El modelo no pudo analizar el comentario.")
        raise SentimentAnalysisError(
            "El modelo no pudo completar el análisis. No se guardó un resultado."
        ) from error
    return label_map[model_label], confidence, extract_keywords(cleaned)


def analyze_comment(comment_id: int) -> tuple[str, float, str] | None:
    row = database.get_comment_for_analysis(comment_id)
    if row is None:
        raise SentimentAnalysisError("No se encontró el comentario solicitado.")
    if row["id_analisis"] is not None:
        return None
    result = _predict(row["comentario"])
    database.save_analysis(comment_id, *result)
    return result


def analyze_pending_comments() -> tuple[int, list[str]]:
    pending_ids = database.get_pending_comment_ids()
    if not pending_ids:
        return 0, []
    try:
        _get_analyzer()
    except SentimentAnalysisError as error:
        return 0, [str(error)]
    analyzed = 0
    errors: list[str] = []
    for comment_id in pending_ids:
        try:
            if analyze_comment(comment_id) is not None:
                analyzed += 1
        except SentimentAnalysisError as error:
            errors.append(f"Comentario {comment_id}: {error}")
    return analyzed, errors
