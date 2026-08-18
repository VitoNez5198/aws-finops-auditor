# ☁️ AWS FinOps & Resource Auditor

[![AWS Free Tier](https://img.shields.io/badge/AWS-Free--Tier-orange?logo=amazon-aws)](https://aws.amazon.com/free/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-purple?logo=terraform)](https://www.terraform.io/)
[![CI/CD GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub--Actions-black?logo=github-actions)](https://github.com/features/actions)

Un microservicio **Serverless** desacoplado y orientado a eventos para la auditoría diaria de costos y recursos en Amazon Web Services (AWS). 

Diseñado bajo principios de **FinOps** (Optimización de Costos) y **Gobierno de Nube**, este sistema inspecciona la cuenta de AWS de forma automatizada, detecta instancias EC2 sin etiquetas obligatorias y notifica el gasto acumulado del mes mediante Webhooks estructurados (Discord, Slack o Telegram).

---

## 🏗️ Arquitectura del Sistema

```
┌──────────────────────────────────────────────────────────────────────────────┐
│            AWS FINOPS & RESOURCE AUDITOR MICROSERVICE ARCHITECTURE           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [ GitHub Repository ] ──▶ [ GitHub Actions CI/CD Pipeline ]                 │
│                                   │ (Ejecuta pytest + terraform apply)       │
│                                   ▼                                          │
│  [ AWS Cloud (Capa Gratuita $0 USD) ]                                        │
│    ├── [ Amazon EventBridge Cron ] (Dispara diariamente a las 08:00 AM)      │
│    │            │                                                            │
│    │            ▼                                                            │
│    ├── [ AWS Lambda (Python 3.11 + Boto3 SDK) ]                              │
│    │       ├── 1. `ec2_auditor.py`: Detecta EC2 sin tags requeridos            │
│    │       ├── 2. `cost_auditor.py`: Obtiene gasto acumulado (USD)           │
│    │       └── 3. `notifier.py`: Prepara payload formateado                  │
│    │            │                                                            │
│    │            ▼                                                            │
│    └── [ Webhook / Amazon SNS ] ──▶ 💬 Mensaje a Discord / Slack / Correo      │
│                                                                              │
│  * Toda la infraestructura definida en módulos de TERRAFORM (.tf)             │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tecnologías y Servicios AWS

- **Capa de Cómputo**: `AWS Lambda` (Python 3.11).
- **Orquestación y Eventos**: `Amazon EventBridge` (Reglas de tiempo tipo Cron).
- **Auditoría & Datos**: `Boto3` (SDK de AWS para Python), `AWS Cost Explorer API` / `AWS Budgets API`.
- **Infraestructura como Código (IaC)**: `Terraform` (Módulos declarativos de `.tf`).
- **Seguridad**: `AWS IAM Roles & Policies` aplicando Mínimo Privilegio.
- **Integración Continua**: `GitHub Actions` con autenticación OIDC.

---

## 🛡️ Capa Gratuita (Free Tier Safety)

Este proyecto fue diseñado con una meta de costo cero ($0 USD/mes):
- **EventBridge**: Gratis (14 millones de eventos/mes).
- **AWS Lambda**: Gratis (1 millón de invocaciones/mes).
- **Sin servidores encendidos 24/7**: No requiere EC2 permanentes ni RDS.

---

## 📂 Estructura del Repositorio

```text
proyecto_aws/
├── .github/
│   └── workflows/
│       └── deploy.yml         # Pipeline CI/CD de GitHub Actions
├── src/
│   ├── lambda_function.py     # Handler principal de la Lambda
│   ├── ec2_auditor.py        # Módulo de auditoría de EC2 y etiquetas
│   ├── cost_auditor.py       # Módulo de auditoría de gasto acumulado
│   └── notifier.py           # Módulo notificador de Webhooks
├── terraform/
│   ├── main.tf               # Proveedor y estado de Terraform
│   ├── variables.tf          # Parámetros (región, webhook URL)
│   ├── iam.tf                # Roles y políticas de menor privilegio
│   ├── lambda.tf             # Recurso Lambda y empaquetado
│   └── eventbridge.tf        # Regla Cron e invocación
├── tests/
│   └── test_auditor.py       # Pruebas unitarias con pytest y moto
├── .gitignore
└── README.md
```

---

## 🚀 Habilidades Demostradas

1. **FinOps & Cloud Governance**: Visibilidad financiera y control de recursos huérfanos.
2. **Infrastructure as Code (IaC)**: Aprovisionamiento profesional con Terraform.
3. **Desarrollo en Python con Boto3**: Uso del SDK oficial de AWS, manejo de errores y peticiones HTTP.
4. **CI/CD Automation**: Automatización de pruebas y despliegue continuo con GitHub Actions.
