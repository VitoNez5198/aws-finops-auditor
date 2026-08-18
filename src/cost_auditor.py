import datetime
import logging
import boto3

logger = logging.getLogger(__name__)


def get_month_to_date_cost(ce_client=None):
    """
    Obtiene el gasto acumulado del mes actual en USD utilizando la API de AWS Cost Explorer.
    Si Cost Explorer no está disponible o falla por permisos, retorna un objeto de respaldo seguro.

    :param ce_client: Cliente de boto3 para Cost Explorer (ce).
    :return: Diccionario con total_cost_usd, start_date, end_date y status.
    """
    if ce_client is None:
        ce_client = boto3.client("ce")

    today = datetime.date.today()
    start_of_month = today.replace(day=1)

    # AWS Cost Explorer requiere que Start y End no sean iguales
    if start_of_month == today:
        end_date = today + datetime.timedelta(days=1)
    else:
        end_date = today

    start_str = start_of_month.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": start_str,
                "End": end_str
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"]
        )

        results = response.get("ResultsByTime", [])
        total_amount = 0.0

        if results:
            total_amount = float(
                results[0].get("Total", {}).get("UnblendedCost", {}).get("Amount", 0.0)
            )

        return {
            "status": "success",
            "total_cost_usd": round(total_amount, 2),
            "start_date": start_str,
            "end_date": end_str,
            "unit": "USD"
        }

    except Exception as e:
        logger.warning(f"No se pudo consultar AWS Cost Explorer ({str(e)}). Usando reporte seguro de respaldo ($0.00).")
        return {
            "status": "fallback",
            "total_cost_usd": 0.0,
            "start_date": start_str,
            "end_date": end_str,
            "unit": "USD",
            "warning": str(e)
        }
