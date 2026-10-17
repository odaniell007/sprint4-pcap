# Estação Solar de Recarga EV Inteligente — Sprint 4 (Pensamento Computacional e Automação com Python · GoodWe)

**Equipe:** 
- Daniel Vieira (RM 573326)
- Giovane Salazar (RM 570396)
- Gustavo Bitencourt (RM 568885)
- Leonardo Takachi (RM 569066)
  
**Disciplina:** Pensamento Computacional e Automação com Python — FIAP

**Vídeo:** `https://youtu.be/mP8a5E5-jrM`

## 1. Resumo
Estação de recarga de veículos elétricos alimentada por geração solar, com armazenamento em bateria e um **algoritmo de agendamento solar-first** que decide, a cada 15 minutos, quando e quanto cada veículo carrega. O objetivo é usar a energia renovável no momento em que ela é gerada, evitar a rede no horário de ponta e garantir que todos os veículos saiam carregados no horário prometido.

## 2. Arquitetura e integração
```
Painéis FV (20 kWp) ─► Inversor híbrido GoodWe GW20K-ET ◄─► Bateria GoodWe Lynx Home D (4 × LX D5.0-10)
                     │  barramento CA da estação ──► Carregadores GoodWe GW7K-HCA / GW11K-HCA
                     │                                       ▲
Medidor inteligente ─┤                                       │ limite de potência por sessão
                     ▼                                       │
        Backend Python (simulacao.py) ── dados de geração/consumo ──► Algoritmo de agendamento
                     │
                     ▼
        SEMS Portal (monitoramento GoodWe) + app/web da estação (Sprint 2): tarifa, pagamento, relatório
```
**Equipamentos e dados dos datasheets GoodWe (versão PT):**

| Equipamento | Dados usados na simulação |
|---|---|
| Inversor GW20K-ET (linha ET 12-30 kW) | Saída nominal 20 kW; 1 entrada de bateria (200~800 V, 50 A); carga/descarga máx. 20 kW; entrada FV máx. 30 kW (2 MPPT); eficiência bateria→CA 97,5%; recursos de controle de carga inteligente e *peak shaving* |
| Bateria Lynx Home D (LX D5.0-10) | 5 kWh utilizáveis, 3 kW nominais e 5 kW de pico (10 s) por módulo; LFP; IP66; modular para conexão em paralelo. Usamos **4 módulos = 20 kWh e 12 kW** (soma linear, premissa nossa) |
| Carregadores GW7K-HCA / GW11K-HCA | 7 kW monofásico (230 V, 32 A) e 11 kW trifásico (400 V, 16 A); IP66; Bluetooth/Wi-Fi; gestão via SEMS |

**Camadas:** (1) geração e armazenamento (FV + bateria), (2) distribuição e medição, (3) inteligência (agendamento), (4) interface e negócio (app web com tarifação por potência, desconto premium, acréscimo de ponta e pagamento PIX/cartão/boleto).

## 3. Alinhamento ao desafio GoodWe e à disciplina
| Componente | Por que foi escolhido | Conceito de Pensamento Computacional / Python |
|---|---|---|
| Inversor híbrido GW20K-ET | Gerencia FV, bateria e carga no mesmo equipamento e permite priorizar autoconsumo | Modelagem dos dados de geração em listas e funções (`pv_profile`) |
| Bateria Lynx Home D (20 kWh) | Desloca energia solar do meio-dia para o horário de ponta | Variáveis de estado (SoC) e estruturas condicionais para carga/descarga |
| Carregadores GW7K-HCA / GW11K-HCA | Controle de potência por sessão, base para o agendamento | Estrutura de dados para sessões (tuplas) e laços de repetição por sessão |
| Monitoramento (SEMS Portal) | Visualização de geração, consumo e bateria | Automação da coleta e exportação de dados (JSON) e geração de gráficos |
| Algoritmo de agendamento | Casa carga flexível com a curva solar | Algoritmo com decomposição, abstração e reconhecimento de padrões |

## 4. Algoritmo inteligente
A cada passo de 15 min:
1. **Sessões obrigatórias:** se adiar a recarga fizer o veículo perder o prazo (energia restante ≥ potência máx. × tempo restante), carrega agora na potência máxima.
2. **Sessões flexíveis:** recebem a **sobra solar**, em ordem de prazo de saída mais próximo (*Earliest Deadline First*).
3. **Bateria:** guarda a sobra restante e cobre déficits (reserva mínima de 10%), reduzindo importação em ponta.
4. A rede nunca carrega a bateria; é só fonte de segurança.

### Pensamento Computacional aplicado
- **Decomposição:** o problema foi dividido em geração FV, bateria, sessões de recarga, tarifação e relatório (funções `pv_profile`, `simular`, `resumo`).
- **Reconhecimento de padrões:** a mesma regra de decisão se repete a cada passo de 15 min, e o perfil solar segue um padrão diário.
- **Abstração:** o sistema real foi simplificado em parâmetros (kWp, kWh, tarifas) concentrados no dicionário `P`, e detalhes como degradação da bateria foram ignorados.
- **Algoritmo:** sequência obrigatórias → flexíveis por prazo (EDF) → bateria, descrita na seção 4.
- **Automação com Python:** um único comando executa a simulação, calcula os indicadores e gera `resultados.json` e `grafico_comparativo.png`, sem etapas manuais.

## 5. Resultados (simulação de 1 dia, 6 veículos, 118 kWh entregues)
Comparação entre **Base** (recarga imediata, sem bateria) e **Inteligente** (algoritmo acima).

| Indicador | Base | Inteligente |
|---|---|---|
| Energia entregue aos veículos | 118,0 kWh | 118,0 kWh |
| Geração FV (dia médio) | 65,6 kWh | 65,6 kWh |
| Autoconsumo solar (parcela da geração aproveitada) | 73,3 % | **100 %** |
| Fração solar da carga (energia da estação vinda do sol) | 33,9 % | **46,2 %** |
| Importação da rede | 93,9 kWh | **72,6 kWh** |
| Importação em horário de ponta | 50,0 kWh | **33,8 kWh** |
| Energia exportada | 17,5 kWh | 0,0 kWh |
| Custo líquido do dia | R$ 96,01 | **R$ 82,13** |
| Energia não entregue | 0 | 0 |

- **Quantitativo:** redução de ~23% na importação da rede, ~32% na importação em ponta e ~R$ 13,88/dia de economia (~14%). Nenhum veículo deixou de receber a energia prometida.
- **Qualitativo:** a estação passa a ser previsível para a rede (menos pico), o usuário não percebe perda de serviço, e o operador ganha dados de uso para decidir tarifa e expansão.
- Gráfico comparativo: `grafico_comparativo.png`. Dados brutos: `resultados.json`.

### Premissas da simulação (editáveis em `simulacao.py`)
**Vindas dos datasheets GoodWe:** inversor de 20 kW, bateria de 20 kWh e 12 kW, eficiência de 97,5% por sentido, carregadores de 7 e 11 kW.
**Informadas pela equipe (tarifa branca, dia útil):** R$ 0,669/kWh fora de ponta (21h30–16h30), R$ 0,985/kWh no intermediário (16h30–17h30 e 20h30–21h30) e R$ 1,480/kWh na ponta (17h30–20h30). Para comparação, a tarifa convencional é R$ 0,7894/kWh.
**Dados públicos:** irradiação de 4,1 kWh/m²/dia para São Paulo (valor aproximado de material da USP/IEE e de estudo do CBENS, a confirmar no SunData/CRESESB) e fator de emissão da rede de 0,0385 kg CO₂/kWh (média do SIN em 2023, MCTI; os meses de jan–abr/2025 ficaram entre 21,5 e 28,9 kg/MWh, então o valor usado é conservador).
**Ainda ilustrativas (substituir por dados reais):** FV de 20 kWp com desempenho global (PR) de 80%, o que gera 20 × 4,1 × 0,80 = 65,6 kWh no dia médio, com perfil senoidal e queda por nuvens entre 13h e 14h30; carga base de 1 kW; crédito de exportação de R$ 0,45/kWh; gasolina de 0,19 kg CO₂/km; consumo do veículo elétrico de 0,15 kWh/km; reserva mínima da bateria de 10%.

## 6. Sustentabilidade e avaliação crítica
**Benefícios:** a energia limpa alimenta o transporte limpo; toda a geração solar do dia é aproveitada (100%, contra 73% no cenário base) e a fração solar da estação sobe de 34% para 46%; na simulação o dia evita ~148 kg de CO₂ frente a veículos a gasolina equivalentes, com apenas ~2,8 kg emitidos pela rede.
**Limitações:** os 20 kWp geram 65,6 kWh no dia médio, bem menos que os ~142 kWh que a estação consome, então mais da metade da energia ainda vem da rede, e o ganho financeiro é moderado (~14%). Para aumentar o ganho, é preciso mais potência FV ou permitir que a bateria carregue da rede fora de ponta (R$ 0,669 contra R$ 1,480 na ponta), o que o algoritmo atual não faz. Além disso: simulação de um dia, perfil solar sintético, sem degradação da bateria, sem perdas de conversão detalhadas e sem validação em hardware real. O algoritmo depende de a **hora de saída informada pelo usuário** ser correta.
**Próximos passos:** integrar dados reais da API do SEMS Portal, previsão de irradiação, otimização por tarifa dinâmica, V2G e assistente virtual para consultar status por voz.

## 7. Tecnologias e referências
Python 3 (simulação/backend), HTML/CSS/JS (interface da Sprint 2), matplotlib (gráficos), GitHub (versionamento). Equipamentos e portal: GoodWe (inversor híbrido, bateria, carregador EV, SEMS Portal). Fontes: datasheets GoodWe em português (linha ET 12-30 kW, Lynx D e linha HCA); MCTI/SIRENE (fator de emissão do SIN); CRESESB/SunData (irradiação solar).

## 8. Como executar
```bash
python simulacao.py   # gera resultados.json e grafico_comparativo.png
```
Estrutura do repositório: `README.md`, `simulacao.py`, `resultados.json`, `grafico_comparativo.png`, `docs/` (diagramas), `web/` (protótipo da Sprint 2).
