PRIMEIRO_ANO = 1990
ULTIMO_ANO_COMPLETO = 2025


def nome_temporada(ano_inicio):
    return f"{ano_inicio}-{str(ano_inicio + 1)[-2:]}"


TEMPORADAS = [nome_temporada(ano) for ano in range(PRIMEIRO_ANO, ULTIMO_ANO_COMPLETO + 1)]
