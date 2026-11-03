CREATE DATABASE IF NOT EXISTS opiniones_productos
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE opiniones_productos;

CREATE TABLE IF NOT EXISTS productos (
    id_producto INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT NULL,
    categoria VARCHAR(100) NOT NULL DEFAULT '',
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_producto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(150) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_cliente),
    UNIQUE KEY uq_clientes_correo (correo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS comentarios_productos (
    id_comentario INT NOT NULL AUTO_INCREMENT,
    id_producto INT NOT NULL,
    id_cliente INT NOT NULL,
    comentario TEXT NOT NULL,
    like_producto BOOLEAN NOT NULL DEFAULT FALSE,
    dislike_producto BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_comentario DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_comentario),
    KEY idx_comentarios_producto (id_producto),
    KEY idx_comentarios_cliente (id_cliente),
    CONSTRAINT fk_comentarios_producto
        FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_comentarios_cliente
        FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_comentario_no_vacio
        CHECK (CHAR_LENGTH(TRIM(comentario)) > 0),
    CONSTRAINT chk_like_dislike_excluyentes
        CHECK (like_producto = FALSE OR dislike_producto = FALSE)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analisis_comentarios (
    id_analisis INT NOT NULL AUTO_INCREMENT,
    id_comentario INT NOT NULL,
    sentimiento VARCHAR(20) NOT NULL,
    puntuacion DECIMAL(5,4) NOT NULL,
    palabras_clave TEXT NULL,
    fecha_analisis DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_analisis),
    UNIQUE KEY uq_analisis_comentario (id_comentario),
    CONSTRAINT fk_analisis_comentario
        FOREIGN KEY (id_comentario) REFERENCES comentarios_productos (id_comentario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_analisis_sentimiento
        CHECK (sentimiento IN ('POSITIVO', 'NEGATIVO', 'NEUTRAL')),
    CONSTRAINT chk_analisis_puntuacion
        CHECK (puntuacion >= 0 AND puntuacion <= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'Notebook HP', 'Producto de ejemplo para probar el registro de opiniones.', 'Informática'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'Notebook HP'
);

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'Auriculares inalámbricos', 'Producto de ejemplo para pruebas.', 'Audio'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'Auriculares inalámbricos'
);

INSERT INTO clientes (nombre, correo)
SELECT 'Cliente de prueba', 'cliente.prueba@example.com'
WHERE NOT EXISTS (
    SELECT 1 FROM clientes WHERE correo = 'cliente.prueba@example.com'
);

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'Laptop Lenovo ThinkPad E14', 'Laptop para trabajo y estudio con procesador Intel Core i5 y 16 GB de memoria.', 'Informatica'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'Laptop Lenovo ThinkPad E14'
);

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'Monitor Dell 24 P2422H', 'Monitor IPS de 24 pulgadas con resolucion Full HD y soporte ajustable.', 'Monitores'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'Monitor Dell 24 P2422H'
);

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'Teclado mecanico Logitech K835', 'Teclado mecanico compacto para oficina y uso diario.', 'Perifericos'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'Teclado mecanico Logitech K835'
);

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'Mouse Logitech M170', 'Mouse inalambrico optico con receptor USB.', 'Perifericos'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'Mouse Logitech M170'
);

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'SSD Kingston NV2 1TB', 'Unidad SSD NVMe de 1 TB para almacenamiento y mejora del rendimiento.', 'Almacenamiento'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'SSD Kingston NV2 1TB'
);

INSERT INTO productos (nombre, descripcion, categoria)
SELECT 'Webcam Logitech C920', 'Camara web Full HD para videollamadas y clases virtuales.', 'Video'
WHERE NOT EXISTS (
    SELECT 1 FROM productos WHERE nombre = 'Webcam Logitech C920'
);
