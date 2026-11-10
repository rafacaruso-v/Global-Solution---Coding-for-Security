"use strict";

const $ = (seletor) => document.querySelector(seletor);

const ROTULOS = { baixo: "Baixo", atencao: "Atenção", alerta: "Alerta", critico: "Crítico" };
const ORIENTACAO = {
  baixo: "Sem previsão de chuva forte agora. Continue acompanhando.",
  atencao: "Chuva forte prevista. Evite áreas de alagamento.",
  alerta: "Risco de alagamento. Evite sair e proteja seus pertences.",
  critico: "Risco crítico. Em área de risco, siga a Defesa Civil (199) e procure um local seguro.",
};
const CHAVE_LOCAL = "alertachuva.minha";

let minha = lerMinha(); // { id, token } guardado só neste aparelho

/* ---------- armazenamento local (pode falhar em modo privado) ---------- */
function lerMinha() {
  try { return JSON.parse(localStorage.getItem(CHAVE_LOCAL)); } catch { return null; }
}
function guardarMinha(valor) {
  minha = valor;
  try {
    if (valor) localStorage.setItem(CHAVE_LOCAL, JSON.stringify(valor));
    else localStorage.removeItem(CHAVE_LOCAL);
  } catch { /* sem armazenamento: segue funcionando nesta sessão */ }
}

/* ---------- chamada à API ---------- */
async function chamar(caminho, { metodo = "GET", corpo, cabecalhos = {} } = {}) {
  const opcoes = { method: metodo, headers: { ...cabecalhos } };
  if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }
  let resposta;
  try {
    resposta = await fetch("/api" + caminho, opcoes);
  } catch {
    throw new Error("Não foi possível falar com o servidor. Verifique sua conexão.");
  }
  if (resposta.status === 204) return null;
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const erro = new Error(dados.erro || "Algo deu errado. Tente novamente.");
    erro.campos = dados.campos;
    erro.status = resposta.status;
    throw erro;
  }
  return dados;
}

function mostrar(elemento, texto, tipo) {
  elemento.className = "msg" + (tipo ? " " + tipo : "");
  elemento.textContent = texto;
}

function textoErro(erro) {
  if (erro.campos) return Object.values(erro.campos).join(" ");
  return erro.message;
}

/* ---------- áreas ---------- */
async function carregarAreas() {
  const areas = await chamar("/areas");
  document.querySelectorAll(".area-select").forEach((sel) => {
    sel.replaceChildren();
    areas.forEach((a) => sel.append(new Option(a.nome, a.id)));
  });
}

/* ---------- risco ---------- */
async function carregarRisco() {
  const areaId = $("#area-risco").value;
  if (!areaId) return;
  const painel = $("#painel-risco");
  painel.classList.add("carregando");
  try {
    const r = await chamar("/risco?area_id=" + encodeURIComponent(areaId));
    painel.className = "risco nivel-" + r.nivel;
    $("#nivel-texto").textContent = ROTULOS[r.nivel] || "–";
    $("#risco-msg").textContent = ORIENTACAO[r.nivel] || "";
    $("#chuva-total").textContent = r.total_24h_mm.toFixed(1) + " mm";
    $("#chuva-pico").textContent = r.pico_1h_mm.toFixed(1) + " mm/h";
    document.querySelectorAll(".escala li").forEach((li) =>
      li.classList.toggle("ativo", li.dataset.nivel === r.nivel));
  } catch (erro) {
    painel.className = "risco";
    $("#nivel-texto").textContent = "–";
    $("#risco-msg").textContent = textoErro(erro);
    $("#chuva-total").textContent = "–";
    $("#chuva-pico").textContent = "–";
  }
}

/* ---------- inscrição (criar / editar / cancelar) ---------- */
function modoEdicao(ativo) {
  $("#bloco-consentimento").hidden = ativo;
  $("#btn-cancelar").hidden = !ativo;
  $("#btn-salvar").textContent = ativo ? "Salvar alterações" : "Receber alertas";
}

async function carregarMinha() {
  if (!minha) return modoEdicao(false);
  try {
    const i = await chamar("/inscricoes/" + encodeURIComponent(minha.id),
      { cabecalhos: { "X-Token": minha.token } });
    $("#apelido").value = i.apelido;
    $("#area-form").value = String(i.area_id);
    $("#nivel").value = i.nivel_minimo;
    modoEdicao(true);
    mostrar($("#form-msg"), "Você já está inscrito. Altere os dados abaixo se precisar.", "");
  } catch {
    guardarMinha(null); // inscrição cancelada ou token inválido
    modoEdicao(false);
  }
}

function dadosDoFormulario() {
  return {
    apelido: $("#apelido").value,
    area_id: Number($("#area-form").value),
    nivel_minimo: $("#nivel").value,
  };
}

async function enviarFormulario(evento) {
  evento.preventDefault();
  const msg = $("#form-msg");
  const botao = $("#btn-salvar");
  botao.disabled = true;
  try {
    if (minha) {
      await chamar("/inscricoes/" + encodeURIComponent(minha.id), {
        metodo: "PUT", corpo: dadosDoFormulario(), cabecalhos: { "X-Token": minha.token },
      });
      mostrar(msg, "Alterações salvas.", "ok");
    } else {
      const nova = await chamar("/inscricoes", {
        metodo: "POST",
        corpo: { ...dadosDoFormulario(), consentimento: $("#consentimento").checked },
      });
      guardarMinha({ id: nova.id, token: nova.token });
      modoEdicao(true);
      msg.className = "msg ok";
      msg.replaceChildren(
        document.createTextNode("Inscrição feita. Seu código de gestão (guarde-o): "),
        Object.assign(document.createElement("code"), { textContent: nova.token }),
      );
    }
  } catch (erro) {
    mostrar(msg, textoErro(erro), "erro");
  } finally {
    botao.disabled = false;
  }
}

async function cancelarInscricao() {
  if (!minha || !confirm("Cancelar sua inscrição? Seus dados serão apagados.")) return;
  try {
    await chamar("/inscricoes/" + encodeURIComponent(minha.id),
      { metodo: "DELETE", cabecalhos: { "X-Token": minha.token } });
    guardarMinha(null);
    $("#form-inscricao").reset();
    modoEdicao(false);
    mostrar($("#form-msg"), "Inscrição cancelada e dados apagados.", "ok");
  } catch (erro) {
    mostrar($("#form-msg"), textoErro(erro), "erro");
  }
}

/* ---------- painel do operador ---------- */
function cabecalhoOperador() {
  return { "X-API-Key": $("#chave").value };
}

async function listarInscritos() {
  const msg = $("#op-msg");
  try {
    const lista = await chamar("/inscricoes", { cabecalhos: cabecalhoOperador() });
    const corpo = $("#tabela-inscritos tbody");
    corpo.replaceChildren();
    lista.forEach((i) => {
      const linha = document.createElement("tr");
      [i.id, i.apelido, i.area_nome, ROTULOS[i.nivel_minimo]].forEach((v) => {
        const celula = document.createElement("td");
        celula.textContent = v; // textContent: nunca interpreta HTML
        linha.append(celula);
      });
      corpo.append(linha);
    });
    $("#tabela-inscritos").hidden = false;
    mostrar(msg, lista.length + " inscrição(ões).", "ok");
  } catch (erro) {
    mostrar(msg, textoErro(erro), "erro");
  }
}

async function dispararAlerta() {
  const msg = $("#op-msg");
  const corpo = { area_id: Number($("#area-op").value) };
  if ($("#simulacao").value) corpo.simulacao = $("#simulacao").value;
  try {
    const r = await chamar("/alertas/disparar",
      { metodo: "POST", corpo, cabecalhos: cabecalhoOperador() });
    if (!r.enviado) {
      mostrar(msg, r.motivo || "Nenhum alerta enviado.", "");
    } else if (r.confirmado) {
      mostrar(msg, `Alerta de nível ${ROTULOS[r.nivel]} entregue e confirmado pelo receptor (${r.destinatarios} inscrito(s)).`, "ok");
    } else {
      mostrar(msg, "Alerta enviado, mas o receptor não confirmou. Verifique se ele está ligado.", "erro");
    }
  } catch (erro) {
    mostrar(msg, textoErro(erro), "erro");
  }
}

/* ---------- inicialização ---------- */
async function iniciar() {
  $("#area-risco").addEventListener("change", carregarRisco);
  $("#form-inscricao").addEventListener("submit", enviarFormulario);
  $("#btn-cancelar").addEventListener("click", cancelarInscricao);
  $("#btn-listar").addEventListener("click", listarInscritos);
  $("#btn-disparar").addEventListener("click", dispararAlerta);
  try {
    await carregarAreas();
    await Promise.all([carregarRisco(), carregarMinha()]);
  } catch (erro) {
    $("#risco-msg").textContent = textoErro(erro);
  }
}

iniciar();
