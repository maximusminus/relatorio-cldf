#!/usr/bin/env python3
"""Gera a landing page e o manifesto de versoes do repositorio relatorio-cldf.

Le a arvore publicada, calcula o sha256 de cada versao de cada artefato e emite
`versoes.json` + `index.html`. Sem dependencia externa: so biblioteca padrao.
Rodar da raiz do repositorio:  python3 publicar.py
"""
import hashlib, html, io, json, os, re, datetime

import relatar

RAIZ = os.path.dirname(os.path.abspath(__file__))
HOJE = datetime.date.today().isoformat()

ARTEFATOS = [
    dict(slug="dossie", titulo="Dossiê BRB · Master · Vorcaro",
         linha="Toda ocorrência das três palavras-chave no acervo aberto da CLDF, com o documento exato.",
         nums=[("743", "ocorrências"), ("281", "no caso Master"), ("66", "proposições"), ("28", "votações")]),
    dict(slug="tramitacao", titulo="REQ 1965/2025 e PL 1882/2025",
         linha="A linha do tempo conjunta do pedido de informação e da lei — e a resposta que nunca veio.",
         nums=[("106", "eventos"), ("5d 17h", "da criação à sanção"), ("9", "emendas"), ("0", "respostas")]),
    dict(slug="dificuldades", titulo="As dificuldades de obter a informação",
         linha="O que existe, o que funciona, o que não funciona, o que está concentrado e fragmentado.",
         nums=[("1.231", "pedidos de informação"), ("0", "respostas legíveis"),
               ("55.610", "documentos sem texto"), ("23 de 48", "tipos nunca legíveis")]),
]

DADOS = [
    ("pedidos-de-informacao.csv", "Os 1.231 requerimentos de informação, com desfecho de cada um"),
    ("tipos-de-documento.csv", "Os 48 tipos de documento e quantos são legíveis"),
    ("ocorrencias.csv", "As 874 ocorrências brutas das três palavras-chave"),
    ("documentos.csv", "Os documentos do caso, com endereço de origem"),
    ("emendas.csv", "As emendas ao PL 1882/2025"),
    ("votacoes.csv", "As votações nominais do caso"),
    ("sessoes.csv", "As sessões em que o caso apareceu"),
    ("anexos_pendentes.csv", "Os 68 documentos do caso que existem só como anexo"),
    ("contagens.json", "Todas as contagens desta série, num único arquivo"),
]


def sha(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def versoes(slug):
    """Toda pasta vN/ do artefato, da mais nova para a mais velha."""
    base = os.path.join(RAIZ, slug)
    if not os.path.isdir(base):
        return []
    vs = []
    for nome in os.listdir(base):
        if re.fullmatch(r"v\d+", nome):
            alvo = os.path.join(base, nome, "index.html")
            if os.path.isfile(alvo):
                st = os.stat(alvo)
                vs.append(dict(v=nome, caminho=f"{slug}/{nome}/", bytes=st.st_size,
                               sha256=sha(alvo),
                               data=datetime.date.fromtimestamp(st.st_mtime).isoformat()))
    return sorted(vs, key=lambda x: int(x["v"][1:]), reverse=True)


def main():
    man = dict(gerado=HOJE, artefatos=[], dados=[])
    for a in ARTEFATOS:
        vs = versoes(a["slug"])
        atual = os.path.join(RAIZ, a["slug"], "index.html")
        man["artefatos"].append(dict(
            slug=a["slug"], titulo=a["titulo"], linha=a["linha"], nums=a["nums"],
            atual=dict(caminho=f"{a['slug']}/", sha256=sha(atual) if os.path.isfile(atual) else None,
                       bytes=os.path.getsize(atual) if os.path.isfile(atual) else 0),
            versoes=vs))
    for nome, desc in DADOS:
        p = os.path.join(RAIZ, "dados", nome)
        if os.path.isfile(p):
            man["dados"].append(dict(arquivo=nome, descricao=desc, bytes=os.path.getsize(p), sha256=sha(p)))

    with io.open(os.path.join(RAIZ, "versoes.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
        f.write("\n")

    with io.open(os.path.join(RAIZ, "index.html"), "w", encoding="utf-8") as f:
        f.write(relatar.injetar(landing(man)))
    print(f"versoes.json e index.html gerados — {len(man['artefatos'])} artefatos, "
          f"{sum(len(a['versoes']) for a in man['artefatos'])} versões, {len(man['dados'])} arquivos de dados")


def landing(man):
    e = html.escape
    cartoes = "\n".join(f"""
    <article class="art">
      <h2><a href="{e(a['atual']['caminho'])}">{e(a['titulo'])}</a></h2>
      <p class="linha">{e(a['linha'])}</p>
      <div class="nums">{''.join(f'<div><b>{e(v)}</b><span>{e(l)}</span></div>' for v, l in a['nums'])}</div>
      <p class="vs">Versões:
        {' '.join(f'<a href="{e(x["caminho"])}" title="{e(x["sha256"][:16])}">{e(x["v"])}</a>' for x in a['versoes'])}
        <span class="sh mono" title="código de conferência da versão atual">{e(a['atual']['sha256'][:16] if a['atual']['sha256'] else '')}</span>
      </p>
    </article>""" for a in man["artefatos"])

    rasc = [("index.html", "BRB · Master · Vorcaro no registro da CLDF"),
            ("dossie.html", "Dossiê BRB–Master, primeira geração"),
            ("tramitacao.html", "Pergunta e Autorização, primeira geração")]
    vizinho = os.path.join(os.path.dirname(RAIZ), "brb-master-vorcaro")
    rascunhos = "\n".join(
        f'<tr><th class="mono">{e(n)}</th><td>{e(d)}</td>'
        f'<td class="n">{f"{os.path.getsize(os.path.join(vizinho, n)):,}".replace(",", ".")}</td>'
        f'<td class="sh">local, não publicado</td></tr>'
        for n, d in rasc if os.path.exists(os.path.join(vizinho, n)))

    prim = man["artefatos"][0]
    exemplo_v = prim["versoes"][0]["caminho"] if prim["versoes"] else prim["atual"]["caminho"]

    def bytes_br(n):
        return f"{n:,}".replace(",", ".")

    linhas = "\n".join(
        f'<tr><th><a href="dados/{e(d["arquivo"])}" title="{e(d["arquivo"])}">{e(d["descricao"])}</a></th>'
        f'<td class="n">{bytes_br(d["bytes"])}</td>'
        f'<td class="mono sh">{e(d["sha256"][:16])}</td></tr>'
        for d in man["dados"])

    return f"""<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatórios adhoc — CLDF</title>
<meta name="description" content="Relatórios reprodutíveis sobre a aquisição do Banco Master pelo BRB e sobre o acesso à informação na Câmara Legislativa do Distrito Federal.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Archivo:wght@400;500;600;700&display=swap">
<style>
:root{{--ground:#eef0f3;--surface:#fff;--ink:#15181d;--muted:#5c6470;--faint:#8a929e;
  --rule:#d6dae1;--rule2:#e6e9ee;--acc:#12626b;--neg:#9a434c}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ground:#11131a;--surface:#181b23;
  --ink:#e7eaef;--muted:#9aa2af;--faint:#727b89;--rule:#2b303b;--rule2:#232833;--acc:#5cbac3;--neg:#dc8b92}}}}
:root[data-theme="dark"]{{--ground:#11131a;--surface:#181b23;--ink:#e7eaef;--muted:#9aa2af;--faint:#727b89;
  --rule:#2b303b;--rule2:#232833;--acc:#5cbac3;--neg:#dc8b92}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:Archivo,Arial,sans-serif;
  font-size:15px;line-height:1.55;-webkit-text-size-adjust:100%}}
.wrap{{max-width:940px;margin:0 auto;padding-inline:16px;padding-block:0 72px}}
h1,h2{{font-family:Newsreader,Georgia,serif;font-weight:600;margin:0;text-wrap:balance}}
.mono{{font-family:ui-monospace,Menlo,Consolas,monospace}}
header{{padding-block:48px 30px;border-bottom:1px solid var(--rule)}}
.kick{{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:600}}
h1{{font-size:clamp(30px,5.6vw,46px);line-height:1.06;margin-top:12px;letter-spacing:-.015em}}
.dek{{margin-top:15px;max-width:62ch;color:var(--muted);font-size:15.5px}}
.art{{background:var(--surface);border:1px solid var(--rule);border-radius:3px;padding:20px 21px;margin-top:16px}}
.art h2{{font-size:22px}}
.art h2 a{{color:inherit;text-decoration:none;border-bottom:2px solid var(--acc)}}
.art h2 a:hover{{color:var(--acc)}}
.linha{{margin:9px 0 0;color:var(--muted);font-size:14px;max-width:66ch}}
.nums{{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(112px,1fr));margin-top:16px}}
.nums div{{border-left:2px solid var(--rule2);padding-left:11px}}
.nums b{{display:block;font-family:Newsreader,serif;font-size:23px;font-weight:600;line-height:1.05;
  font-variant-numeric:tabular-nums}}
.nums span{{display:block;font-size:11.5px;color:var(--faint);margin-top:4px}}
.vs{{margin:16px 0 0;padding-top:13px;border-top:1px solid var(--rule2);font-size:12.5px;color:var(--faint)}}
.vs a{{display:inline-block;font-family:ui-monospace,monospace;font-size:12px;padding:3px 9px;margin-right:5px;
  border:1px solid var(--rule);border-radius:100px;color:var(--muted);text-decoration:none}}
.vs a:hover{{border-color:var(--acc);color:var(--acc)}}
.sh{{color:var(--faint);font-size:11px}}
h2.sec{{font-size:22px;margin-top:44px}}
p.sub{{color:var(--muted);font-size:14px;max-width:66ch;margin-top:8px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:14px}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--rule2);vertical-align:top}}
td.n{{text-align:right;font-family:ui-monospace,monospace;white-space:nowrap}}
th a{{color:var(--acc)}}
sup.nref a{{text-decoration:none;font-weight:600;padding:0 1px;color:var(--acc)}}
section.notas-fim{{margin-top:40px;padding-top:16px;border-top:1px solid var(--rule)}}
section.notas-fim h2{{font-size:18px}}
ol.notas{{font-size:13px;line-height:1.5;padding-left:22px;margin:8px 0 0;color:var(--muted)}}
ol.notas li{{margin:5px 0}}
ol.notas a{{color:var(--acc);text-decoration:none}}
footer{{margin-top:46px;padding-top:22px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--faint);
  max-width:76ch;line-height:1.6}}
footer a{{color:var(--acc)}}
</style>
<div class="wrap">
<header>
  <div class="kick">Dados abertos · Câmara Legislativa do Distrito Federal</div>
  <h1>Relatórios adhoc<br>sobre o que a CLDF publica — e sobre o que não publica</h1>
  <p class="dek">Cada relatório abaixo foi feito só com dados abertos, lidos em endereços públicos, sem senha
  nem cadastro. As planilhas que os sustentam estão nesta mesma página. Nada aqui pede que se acredite:
  qualquer pessoa pode refazer as contas.<sup class="nref"><a href="#nota-1" id="ref-1">1</a></sup></p>
</header>

<h2 class="sec">Conjunto <span class="mono">relatorio-cldf</span></h2>
<p class="sub">O BRB, o Banco Master e Daniel Vorcaro no acervo aberto da Casa: as ocorrências,
a tramitação conjunta do pedido de informação e da autorização, e o que impede um cidadão de
chegar sozinho a esses números.</p>
{cartoes}

<h2 class="sec">Ainda não publicados</h2>
<p class="sub">A primeira geração destes mesmos relatórios, anterior à publicação. Fica registrada
aqui por honestidade de percurso: existe, não está no ar, e foi substituída pelas versões acima.</p>
<table>
<thead><tr><th>Rascunho</th><th>O que é</th><th class="n">Tamanho</th><th>Estado</th></tr></thead>
<tbody>
{rascunhos}
</tbody></table>

<h2 class="sec">Os dados</h2>
<p class="sub">As planilhas que sustentam os relatórios acima, em formato aberto. Cada uma tem um código de
conferência publicado, para que qualquer alteração futura possa ser percebida.<sup class="nref"><a href="#nota-2" id="ref-2">2</a></sup></p>
<table>
<thead><tr><th>Arquivo</th><th class="n">Tamanho</th><th>Código de conferência</th></tr></thead>
<tbody>
{linhas}
</tbody></table>

<h2 class="sec">Como as versões funcionam</h2>
<p class="sub">Cada relatório tem um endereço estável — <span class="mono">/dossie/</span>,
<span class="mono">/tramitacao/</span>, <span class="mono">/dificuldades/</span> — que sempre aponta para a
versão mais recente. Cada versão também fica congelada no seu próprio endereço
(<span class="mono">/{exemplo_v}</span>, por exemplo) e nunca muda depois de publicada. Uma
<a href="versoes.json">lista de todas as versões</a>, com data, tamanho e código de conferência, garante
que uma citação feita hoje continue verificável amanhã.<sup class="nref"><a href="#nota-3" id="ref-3">3</a></sup></p>

<section class="notas-fim" aria-label="Notas">
<h2>Notas</h2>
<ol class="notas">
<li id="nota-1">Os dados foram colhidos por requisições públicas e não autenticadas; as planilhas estão em CSV,
e as contagens, em JSON. <a class="volta" href="#ref-1" aria-label="voltar ao texto">↩</a></li>
<li id="nota-2">O código de conferência é o <i>hash</i> SHA-256 do arquivo; a tabela mostra os seus primeiros 16
caracteres. O nome de cada arquivo aparece ao passar o cursor sobre o link. <a class="volta" href="#ref-2" aria-label="voltar ao texto">↩</a></li>
<li id="nota-3">O manifesto <span class="mono">versoes.json</span> traz, para cada versão, o SHA-256 completo,
o tamanho em bytes e a data. <a class="volta" href="#ref-3" aria-label="voltar ao texto">↩</a></li>
<li id="nota-4">A API pública de proposições da CLDF (<span class="mono">ple.cl.df.gov.br/pleservico/api/public</span>),
o portal CKAN de dados abertos da Casa, os painéis Power BI do Portal da Transparência e a Biblioteca
Digital. <a class="volta" href="#ref-4" aria-label="voltar ao texto">↩</a></li>
</ol>
</section>

<footer>
<p>Gerado em {e(man['gerado'])}. Relatórios e código sob licença de uso não comercial; os dados derivados sob
CC BY-SA 4.0, a mesma licença que a fonte declara. As fontes são os dados abertos de proposições da CLDF, o portal
de dados abertos da Casa, os painéis do Portal da Transparência e a Biblioteca Digital.<sup class="nref"><a href="#nota-4" id="ref-4">4</a></sup>
Nenhum sistema foi acessado com senha e nenhuma informação restrita foi usada.</p>
</footer>
</div>
</html>
"""


if __name__ == "__main__":
    main()
