from datetime import datetime, timezone
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, constr

app = FastAPI(
    title="API Fila de Atendimento",
    description="Avaliação: Desenvolvimento de APIs e Microsserviços",
    version="1.0.0",
)

# ----------------------------
# MODELOS (Pydantic)
# ----------------------------
TipoAtendimento = Literal["N", "P"]  # Normal ou Prioritário

class ClienteIn(BaseModel):
    nome: constr(strip_whitespace=True, min_length=1, max_length=20) = Field(..., description="Nome (obrigatório, até 20 chars)")
    tipo: TipoAtendimento = Field(..., description="Tipo de atendimento: 'N' ou 'P'")

class Cliente(BaseModel):
    posicao: int
    nome: str
    chegada: datetime
    tipo: TipoAtendimento
    atendido: bool = False

# ----------------------------
# "BANCO" EM MEMÓRIA
# ----------------------------
fila: List[Cliente] = []

def agora_utc() -> datetime:
    return datetime.now(timezone.utc)

def ordenar_recalcular_posicoes():
    """
    Reaplica a regra de prioridade e renumera posições (1..n) para não atendidos.
    Prioridade: 'P' antes de 'N'; dentro do mesmo tipo, mantém ordem de chegada.
    """
    nao_atendidos = [c for c in fila if not c.atendido]
    atendidos = [c for c in fila if c.atendido]

    nao_atendidos.sort(key=lambda c: (0 if c.tipo == "P" else 1))
    for i, c in enumerate(nao_atendidos, start=1):
        c.posicao = i

    fila.clear()
    fila.extend(nao_atendidos + atendidos)

def encontrar_por_posicao(posicao: int) -> Optional[Cliente]:
    for c in fila:
        if c.posicao == posicao:
            return c
    return None

# ----------------------------
# ENDPOINTS
# ----------------------------

@app.get("/", summary="Status da API")
def raiz():
    return {
        "mensagem": "API Fila de Atendimento online",
        "docs": "/docs",
        "endpoints": ["/fila", "/fila/{id}"]
    }


@app.get("/fila", response_model=List[Cliente], summary="Lista a fila (apenas não atendidos)")
def get_fila():
    ordenar_recalcular_posicoes()
    return [c for c in fila if not c.atendido]


@app.get("/fila/{id}", response_model=Cliente, summary="Detalhes de um cliente pela posição")
def get_fila_id(id: int):
    ordenar_recalcular_posicoes()
    cliente = encontrar_por_posicao(id)
    if not cliente or cliente.atendido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Não existe cliente na posição {id}.",
        )
    return cliente


@app.post("/fila", response_model=Cliente, status_code=status.HTTP_201_CREATED, summary="Adiciona novo cliente à fila")
def post_fila(novo: ClienteIn):
    cliente = Cliente(
        posicao=999999,
        nome=novo.nome,
        chegada=agora_utc(),
        tipo=novo.tipo,
        atendido=False,
    )
    fila.append(cliente)
    ordenar_recalcular_posicoes()
    return cliente


@app.put("/fila", response_model=List[Cliente], summary="Avança a fila (decrementa 1 posição)")
def put_fila():
    ordenar_recalcular_posicoes()
    primeiro = encontrar_por_posicao(1)
    if primeiro:
        primeiro.posicao = 0
        primeiro.atendido = True
    ordenar_recalcular_posicoes()
    return [c for c in fila if not c.atendido]


@app.delete("/fila/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove cliente por posição e reordena")
def delete_fila_id(id: int):
    ordenar_recalcular_posicoes()
    cliente = encontrar_por_posicao(id)
    if not cliente or cliente.atendido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Não existe cliente na posição {id}.",
        )
    fila.remove(cliente)
    ordenar_recalcular_posicoes()
    return
