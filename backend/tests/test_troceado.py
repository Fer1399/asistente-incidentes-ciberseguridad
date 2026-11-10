from app.extraccion import Pagina, limpiar
from app.troceado import trocear


def test_respeta_tamano_y_paginas():
    texto = "\n\n".join(f"Párrafo {i}. " + "palabra " * 40 for i in range(20))
    fragmentos = trocear([Pagina(1, texto), Pagina(2, texto)], tamano=500, solape=80)

    assert len(fragmentos) > 4
    assert all(len(f.texto) <= 500 + 80 for f in fragmentos)
    assert {f.pagina for f in fragmentos} == {1, 2}
    assert [f.indice for f in fragmentos] == list(range(len(fragmentos)))


def test_solape_entre_fragmentos():
    texto = " ".join(f"frase{i}." for i in range(400))
    fragmentos = trocear([Pagina(1, texto)], tamano=300, solape=60)

    for anterior, siguiente in zip(fragmentos, fragmentos[1:]):
        primera_palabra = siguiente.texto.split()[0]
        assert primera_palabra in anterior.texto


def test_descarta_fragmentos_vacios():
    assert trocear([Pagina(1, "   \n\n  "), Pagina(2, "corto")]) == []


def test_limpiar_une_palabras_partidas():
    assert limpiar("contra-\nseña   segura\n\n\n\nfin") == "contraseña segura\n\nfin"
