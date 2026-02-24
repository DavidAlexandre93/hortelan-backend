# Análise de aderência do backend ao núcleo estratégico do Hortelan

Escala usada neste documento:

- **Atende parcialmente**: existe infraestrutura base, mas faltam casos de uso/entidades/endpoints para fechar a funcionalidade.
- **Não atende ainda**: não há implementação dedicada no backend atual.

## Resultado geral

O backend atual **não atende integralmente** ao núcleo estratégico completo. Ele está mais maduro no eixo de **IoT/telemetria/comandos**, com endpoints e casos de uso funcionando, e tem um **catálogo de requisitos** que já sinaliza cobertura parcial. Porém, a maioria dos módulos estratégicos de produto (comunidade, marketplace, gamificação, agenda, recomendações e backoffice completo) ainda está em fase de estruturação. 

## Matriz de cobertura das funcionalidades estratégicas

| Funcionalidade estratégica | Status atual | Evidência técnica |
| --- | --- | --- |
| Cadastro e gestão de hortas/plantas | **Não atende ainda** | Está catalogado como requisito (2.1 e 3.1), mas fora do conjunto marcado como implementado. |
| Integração com sensores e dispositivos IoT | **Atende parcialmente** | Existem endpoints de telemetria/comandos e snapshot de dispositivo; requisitos 4.1, 4.4, 4.5 e 4.6 estão marcados como implementados. |
| Dashboard de monitoramento | **Não atende ainda (backend dedicado)** | Requisitos de dashboard (5.x) existem no catálogo, mas não estão marcados como implementados. |
| Automação por regras | **Não atende ainda** | Requisitos de automação (6.x) estão no catálogo sem marcação de implementação. |
| Alertas e notificações | **Não atende ainda** | Requisitos (10.x) aparecem no catálogo, sem implementação marcada. |
| Agenda de tarefas de cultivo | **Não atende ainda** | Requisitos (7.x) presentes no catálogo, não implementados. |
| Recomendações inteligentes (e diagnóstico por foto) | **Não atende ainda** | Requisitos (9.x) existem no catálogo, mas sem implementação funcional marcada. |
| Comunidade com compartilhamento de experiências | **Não atende ainda** | Requisitos de comunidade (12.x) no catálogo sem implementação. |
| Templates/receitas de cultivo e automação | **Não atende ainda** | Requisitos (13.x) no catálogo sem implementação. |
| Marketplace com recomendações contextuais | **Não atende ainda** | Requisitos de loja/marketplace (14.x) no catálogo sem implementação. |
| Gamificação/recompensas | **Não atende ainda** | Requisitos (15.x) no catálogo sem implementação. |
| Backoffice/admin + suporte + LGPD | **Atende parcialmente (escopo restrito)** | Só há marcação para auditoria/logs (25.1) e catálogo de requisitos de admin/suporte/LGPD (18.x, 19.x, 21.3), ainda não marcados como implementados. |

## Próximos passos recomendados (ordem de impacto)

1. **Modelagem de domínio de horta/planta/tarefas** para habilitar cadastro e agenda (2.x, 3.x, 7.x).
2. **Motor de regras e alertas** (6.x + 10.x), reaproveitando pipeline já existente de telemetria/comandos.
3. **Camada de recomendações** inicialmente baseada em regras (9.1/9.2), deixando visão computacional (9.3/9.4) como etapa posterior.
4. **Módulos de produto** (12.x, 13.x, 14.x, 15.x) com rollout incremental por domínio.
5. **Backoffice/LGPD/suporte** (18.x, 19.x, 21.x) com trilha de auditoria e consentimento evoluindo de 25.1.
