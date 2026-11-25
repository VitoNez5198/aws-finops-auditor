# AWS FinOps & Resource Auditor

[![AWS Serverless](https://img.shields.io/badge/AWS-Serverless-orange?logo=amazon-aws)](https://aws.amazon.com/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-purple?logo=terraform)](https://www.terraform.io/)
[![CI/CD GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub--Actions-black?logo=github-actions)](https://github.com/features/actions)

> Microservicio serverless en AWS provisionado con **Terraform** para auditoría diaria de gobierno de etiquetas en EC2 y seguimiento de gasto mensual en **Cost Explorer**, con alertas estructuradas por webhook y pipeline CI/CD en GitHub Actions.

---

## Contexto y Problema

En cuentas AWS compartidas o de laboratorio, dos fugas frecuentes de gobierno y FinOps son:
- **Recursos sin etiquetar:** instancias EC2 creadas sin tags obligatorios (`Owner`, `Environment`), lo que impide asignar costos por proyecto o responsable.
- **Falta de visibilidad diaria del gasto:** detectar anomalías recién al cierre de factura mensual.

Este proyecto automatiza una auditoría diaria programada sin servidores encendidos 24/7, validando cumplimiento de etiquetas en EC2 y reportando el gasto acumulado del mes vía webhook (Discord / Slack).

---

## Arquitectura del Sistema

Toda la infraestructura se define de forma declarativa en [terraform/](terraform/) y se despliega mediante [.github/workflows/deploy.yml](.github/workflows/deploy.yml):

![Arquitectura Serverless de AWS FinOps Auditor](docs/architecture.png)

### Flujo de Trabajo y Rol de cada Servicio

1. **Despliegue automatizado (`GitHub Actions` + `Terraform`):** Cada push a `main` ejecuta primero las pruebas unitarias con `pytest` y `moto`, y luego aplica la infraestructura en AWS mediante Terraform (`init`, `validate`, `plan`, `apply`).
2. **Programación diaria (`Amazon EventBridge`):** Una regla programada (`cron`) dispara automáticamente la función auditora una vez al día sin necesidad de mantener servidores encendidos.
3. **Ejecución y permisos (`AWS Lambda` + `AWS IAM`):** La función Lambda (Python 3.11) ejecuta la auditoría utilizando un rol IAM con permisos estrictos de solo lectura sobre EC2 y Cost Explorer.
4. **Auditoría de recursos y gasto (`Amazon EC2` + `AWS Cost Explorer`):** Lambda revisa las instancias EC2 activas para detectar aquellas sin etiquetas obligatorias (`Owner`, `Environment`) y consulta el gasto acumulado del mes en Cost Explorer.
5. **Observabilidad y alertas (`Amazon CloudWatch` + `Webhook`):** Los registros de cada ejecución quedan en CloudWatch Logs y el resumen diario se envía mediante un webhook a Discord o Slack.

---

## Decisiones Técnicas

- **Lambda minimalista (`128 MB`, timeout `30s`):** la carga es I/O-bound (llamadas Boto3 a EC2, Cost Explorer y un POST HTTP), por lo que 128 MB minimiza el costo de ejecución sin degradar la latencia.
- **Empaquetado reproducible en Terraform (`archive_file` + `source_code_hash`):** detecta cambios en `src/` automáticamente y actualiza el código de la función solo cuando cambia el hash SHA-256.
- **Nombres sin colisiones en IAM (`name_prefix`):** evita errores al recrear roles o políticas en redespliegues de Terraform.
- **Pruebas unitarias aisladas con `moto`:** simula llamadas a AWS EC2 y Cost Explorer en `pytest` sin tocar cuentas reales ni generar costos durante el CI.

---

## Seguridad e IAM

Controles implementados en [terraform/iam.tf](terraform/iam.tf) y [terraform/eventbridge.tf](terraform/eventbridge.tf):

- **Principio de menor privilegio (solo lectura en auditoría):** el rol de Lambda solo permite `ec2:DescribeInstances`, `ec2:DescribeTags`, `ce:GetCostAndUsage` y escritura en CloudWatch Logs; no puede modificar ni terminar recursos.
- **Invocación restringida por origen:** `aws_lambda_permission` autoriza únicamente al principal `events.amazonaws.com` condicionado por el `source_arn` exacto de la regla de EventBridge.
- **Protección de secretos en IaC:** la variable `webhook_url` está marcada con `sensitive = true` en [terraform/variables.tf](terraform/variables.tf) para no exponer la URL en logs de `terraform plan`.
- **Hardening previsto para producción:**
  - Migrar la autenticación de `deploy.yml` de Access Keys estáticas a **GitHub OIDC + IAM Role** (`id-token: write` ya está declarado en el workflow).
  - Configurar un **backend remoto de Terraform** (S3 cifrado + bloqueo de estado) en lugar de estado local efímero en el runner.
  - Almacenar `WEBHOOK_URL` en **SSM Parameter Store (SecureString)** o **Secrets Manager** en vez de variable de entorno en texto plano.
  - Acotar el `Resource` de CloudWatch Logs al ARN del Log Group de la función.

---

## FinOps y Control de Costos

Desglose transparente para **1 ejecución diaria** (`cron(0 13 * * ? *)`, ~30 ejecuciones/mes):

| Servicio AWS | Uso mensual estimado | Costo estimado |
| :--- | :--- | :--- |
| **Amazon EventBridge** | 30 eventos programados | **$0.00 USD** (capa gratuita) |
| **AWS Lambda** | 30 invocaciones × 128 MB (< 5s c/u) | **$0.00 USD** (Free Tier: 1M req/mes) |
| **CloudWatch Logs** | < 5 MB de logs | **$0.00 USD** (Free Tier: 5 GB/mes) |
| **AWS Cost Explorer API** | 30 llamadas `ce:GetCostAndUsage` ($0.01/llamada) | **~$0.30 USD/mes** |

> Sin instancias EC2 ni bases de datos encendidas 24/7. El único costo variable es la API de Cost Explorer ($0.01 por consulta); si se requiere estricto $0.00, puede reemplazarse por notificaciones directas de **AWS Budgets**.

---

## Estructura del Repositorio

```text
aws-finops-auditor/
├── .github/
│   └── workflows/
│       └── deploy.yml         # Pipeline CI/CD: pytest + terraform plan/apply
├── docs/
│   ├── architecture.drawio    # Fuente editable del diagrama (Draw.io / AWS4)
│   └── architecture.png       # Diagrama de arquitectura serverless y CI/CD
├── src/
│   ├── lambda_function.py     # Handler principal de AWS Lambda
│   ├── ec2_auditor.py         # Auditoría de instancias EC2 sin etiquetas obligatorias
│   ├── cost_auditor.py        # Consulta de gasto mensual en Cost Explorer
│   └── notifier.py            # Envío de alertas formateadas vía webhook
├── terraform/
│   ├── main.tf                # Providers AWS y archive
│   ├── variables.tf           # Región, entorno, cron, tags obligatorias, webhook
│   ├── iam.tf                 # Rol y política IAM de solo lectura
│   ├── lambda.tf              # Empaquetado ZIP y función Lambda
│   ├── eventbridge.tf         # Regla Cron, target y permiso de invocación
│   └── outputs.tf             # ARNs y nombre de función desplegada
├── tests/
│   └── test_auditor.py        # Pruebas unitarias con pytest y moto
├── .gitignore
└── README.md
```

---

## Pruebas y Despliegue

### Pruebas locales
```bash
pip install pytest moto boto3
pytest tests/ -v
```

### Despliegue manual con Terraform
```bash
cd terraform
terraform init
terraform validate
terraform plan -var="webhook_url=https://discord.com/api/webhooks/..."
terraform apply -var="webhook_url=https://discord.com/api/webhooks/..."
```

---

## Autor

**Víctor Martínez** — Junior Cloud Engineer | AWS, FinOps & Applied AI  
AWS Certified Cloud Practitioner • AWS Cloud re/Start • En preparación para SAA-C03

- **Portafolio:** [vitonez5198.github.io/Portfolio-VM](https://vitonez5198.github.io/Portfolio-VM/)
- **LinkedIn:** [victor-ms-dev](https://www.linkedin.com/in/victor-ms-dev/)
- **GitHub:** [@VitoNez5198](https://github.com/VitoNez5198)
