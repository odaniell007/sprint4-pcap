"""Sprint 4 Pensamento Computacional e Automação com Python - Simulação integrada: FV + bateria + recarga EV com agendamento inteligente.
Compara cenário BASE (recarga imediata, sem bateria) x INTELIGENTE (solar-first + bateria + EDF).
Todas as premissas estão no dicionário P (edite e rode de novo)."""
import json, math, random

P = dict(pv_kwp=20.0, inv_kw=20.0, bat_kwh=20.0, bat_kw=12.0, soc_min=0.10, eta=0.975, base_kw=1.0,
         tarifa_fora=0.669, tarifa_inter=0.985, tarifa_ponta=1.480, ponta=(17.5, 20.5),
         inter=((16.5, 17.5), (20.5, 21.5)),  # tarifa branca 
         credito_export=0.45,
         irradiacao=4.1, pr=0.80, fator_rede=0.0385, gasolina_kg_km=0.19, ev_kwh_km=0.15, seed=7)
DT = 0.25  # h
# (chegada h, saída h, energia kWh, potência máx kW)
SESSOES = [(8, 17, 20, 7), (9.5, 16, 15, 7), (11, 19, 25, 11),
           (12.5, 14.5, 10, 11), (17.5, 22, 30, 11), (18, 23, 18, 7)]

def pv_profile():
    random.seed(P["seed"]); out = []
    for i in range(96):
        h = i * DT
        s = max(0.0, math.sin(math.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0.0
        nuvem = 0.55 if 13 <= h < 14.5 else 1.0  # passagem de nuvens
        out.append(s * nuvem * random.uniform(0.95, 1.0))
    alvo = P["pv_kwp"] * P["irradiacao"] * P["pr"]  # kWh/dia = kWp x irradiação (kWh/m²/dia) x desempenho (PR)
    k = alvo / (sum(out) * DT)
    return [v * k for v in out]

def peak(h): return P["ponta"][0] <= h < P["ponta"][1]
def tarifa(h):
    if peak(h): return P["tarifa_ponta"]
    if any(a <= h < b for a, b in P["inter"]): return P["tarifa_inter"]
    return P["tarifa_fora"]

def simular(inteligente):
    pv = pv_profile(); soc = P["bat_kwh"] * 0.3 if inteligente else 0.0
    rest = [s[2] for s in SESSOES]; r = dict(imp=0, exp=0, imp_ponta=0, custo=0, pv_tot=sum(pv)*DT,
        pv_auto=0, ev=0, curva=[], bat=[])
    for i in range(96):
        h = i * DT; ativos = [k for k, s in enumerate(SESSOES) if s[0] <= h < s[1] and rest[k] > 1e-9]
        ev = {}
        surplus = max(0, pv[i] - P["base_kw"])
        if not inteligente:
            for k in ativos: ev[k] = min(SESSOES[k][3], rest[k] / DT)
        else:
            for k in ativos:  # obrigatória: se adiar, perde o prazo
                tl = SESSOES[k][1] - h
                if rest[k] >= (tl - DT) * SESSOES[k][3] - 1e-9: ev[k] = min(SESSOES[k][3], rest[k] / DT)
            livre = surplus - sum(ev.values())
            for k in sorted(ativos, key=lambda k: SESSOES[k][1]):  # EDF com sobra solar
                if k not in ev and livre > 0.5:
                    p = min(SESSOES[k][3], rest[k] / DT, livre); ev[k] = p; livre -= p
        for k, p in ev.items(): rest[k] -= p * DT
        carga = P["base_kw"] + sum(ev.values()); r["ev"] += sum(ev.values()) * DT
        direto = min(pv[i], carga, P["inv_kw"]); falta = carga - direto; sobra = pv[i] - direto
        if inteligente:
            if sobra > 0:  # carrega bateria
                c = min(sobra, P["bat_kw"], (P["bat_kwh"] - soc) / (DT * P["eta"])); soc += c * DT * P["eta"]; sobra -= c
            if falta > 0:  # descarrega bateria
                d = min(falta, P["bat_kw"], P["inv_kw"] - direto, (soc - P["soc_min"] * P["bat_kwh"]) * P["eta"] / DT)
                d = max(d, 0); soc -= d * DT / P["eta"]; falta -= d
        t = tarifa(h)
        r["imp"] += falta * DT; r["exp"] += sobra * DT
        r["custo"] += falta * DT * t - sobra * DT * P["credito_export"]
        if peak(h): r["imp_ponta"] += falta * DT
        r["pv_auto"] += (pv[i] - sobra) * DT
        r["curva"].append(dict(h=h, pv=round(pv[i], 2), carga=round(carga, 2), rede=round(falta, 2)))
        r["bat"].append(round(soc, 2))
    r["nao_atendido"] = round(sum(rest), 2)
    return r

def resumo(r):
    ev_km = r["ev"] / P["ev_kwh_km"]
    return dict(energia_ev_kwh=round(r["ev"], 1), fv_gerado_kwh=round(r["pv_tot"], 1),
        autoconsumo_pct=round(100 * r["pv_auto"] / r["pv_tot"], 1),
        fracao_solar_pct=round(100 * r["pv_auto"] / (r["ev"] + P["base_kw"] * 24), 1), import_rede_kwh=round(r["imp"], 1),
        import_ponta_kwh=round(r["imp_ponta"], 1), export_kwh=round(r["exp"], 1),
        custo_liquido_rs=round(r["custo"], 2), co2_rede_kg=round(r["imp"] * P["fator_rede"], 2),
        co2_gasolina_evitado_kg=round(ev_km * P["gasolina_kg_km"] - r["imp"] * P["fator_rede"], 1),
        energia_nao_entregue_kwh=r["nao_atendido"])

if __name__ == "__main__":
    b, s = simular(False), simular(True); rb, rs = resumo(b), resumo(s)
    json.dump(dict(premissas=P, base=rb, inteligente=rs), open("resultados.json", "w"), indent=2, ensure_ascii=False)
    for k in rb: print(f"{k:28s} base={rb[k]:>9}  inteligente={rs[k]:>9}")
    print("economia diária R$", round(rb["custo_liquido_rs"] - rs["custo_liquido_rs"], 2))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True); H = [c["h"] for c in s["curva"]]
        for a, r, t in ((ax[0], b, "Base: recarga imediata, sem bateria"), (ax[1], s, "Inteligente: solar-first + bateria + EDF")):
            a.plot(H, [c["pv"] for c in r["curva"]], label="FV (kW)", color="orange")
            a.plot(H, [c["carga"] for c in r["curva"]], label="Carga estação (kW)", color="tab:blue")
            a.fill_between(H, [c["rede"] for c in r["curva"]], alpha=.35, color="red", label="Importação da rede (kW)")
            a.axvspan(*P["ponta"], color="gray", alpha=.15); a.set_title(t); a.legend(loc="upper left"); a.set_ylabel("kW")
        ax[1].set_xlabel("Hora do dia"); plt.tight_layout(); plt.savefig("grafico_comparativo.png", dpi=130)
    except ImportError: print("matplotlib ausente: gráfico não gerado")