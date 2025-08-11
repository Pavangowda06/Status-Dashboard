from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

datadog_regions = {
    "EU": "https://status.datadoghq.eu",
    "US3": "https://status.us3.datadoghq.com",
    "US5": "https://status.us5.datadoghq.com",
    "AP1": "https://status.ap1.datadoghq.com",
    "GovCloud": "https://status.ddog-gov.com",
    "AP2": "https://status.ap2.datadoghq.com"
}

github_components_to_show = [
    "Git Operations", "Webhooks", "API Requests", "Issues", "Pull Requests",
    "Actions", "Packages", "Pages", "Codespaces", "Copilot"
]

def calculate_status_color(non_operational_count):
    if non_operational_count == 0:
        return "green"
    elif non_operational_count <= 2:
        return "orange"
    else:
        return "red"

def calculate_status_label(non_operational_count):
    if non_operational_count == 0:
        return "operational"
    elif non_operational_count <= 2:
        return "minor issue"
    else:
        return "degraded"

@app.get("/", response_class=HTMLResponse)
async def mainstatus_page(request: Request):
    details = {}
    status_colors = {}

    components = {}

    async with httpx.AsyncClient(timeout=10.0) as client:

        # GitHub
        github_components = {}
        try:
            gh_res = await client.get("https://www.githubstatus.com/api/v2/status.json")
            gh_res.raise_for_status()
        except Exception as e:
            details["github"] = f"error: {str(e)}"

        try:
            ghc_res = await client.get("https://www.githubstatus.com/api/v2/components.json")
            ghc_res.raise_for_status()
            for comp in ghc_res.json().get("components", []):
                name = comp.get("name")
                status = comp.get("status")
                if name in github_components_to_show:
                    github_components[name] = {
                        "status": status,
                        "severity": status if status.lower() != "operational" else None
                    }
        except:
            github_components = {}

        github_components_sorted = dict(sorted(
            github_components.items(),
            key=lambda item: item[1]["status"].lower() == "operational"
        ))

        non_operational = sum(1 for val in github_components.values() if val["status"].lower() != "operational")
        status_colors["github"] = calculate_status_color(non_operational)
        details["github"] = calculate_status_label(non_operational)
        components["github"] = github_components_sorted


        # Azure (No change)
        try:
            azure_res = await client.get("https://azure.status.microsoft/en-us/status/feed/", follow_redirects=True)
            azure_res.raise_for_status()
            details["azure"] = "operational" if "<entry>" not in azure_res.text else "error"
        except Exception as e:
            details["azure"] = f"error: {str(e)}"

        # AWS (No change)
        try:
            aws_res = await client.get("https://status.aws.amazon.com/rss/all.rss", follow_redirects=True)
            aws_res.raise_for_status()
            details["aws"] = "operational" if "<item>" not in aws_res.text else "error"
        except Exception as e:
            details["aws"] = f"error: {str(e)}"

        status_colors["aws"] = "green" if details["aws"] == "operational" else "red"

        # Datadog Global
        datadog_regions_status = {}
        try:
            dd_res = await client.get("https://status.datadoghq.com/api/v2/status.json")
            dd_res.raise_for_status()
        except Exception as e:
            details["datadog"] = f"error: {str(e)}"

        for region, url in datadog_regions.items():
            try:
                res = await client.get(f"{url}/api/v2/status.json")
                res.raise_for_status()
                data = res.json()
                indicator = data.get("status", {}).get("indicator", "unknown")
                status = "operational" if indicator == "none" else indicator
                datadog_regions_status[region] = {
                    "status": status,
                    "severity": indicator if status != "operational" else None
                }
            except:
                datadog_regions_status[region] = {
                    "status": "error",
                    "severity": "unknown"
                }

        datadog_regions_sorted = dict(sorted(
            datadog_regions_status.items(),
            key=lambda item: item[1]["status"] == "operational"
        ))

        non_operational_dd = sum(1 for val in datadog_regions_status.values() if val["status"] != "operational")
        status_colors["datadog"] = calculate_status_color(non_operational_dd)
        details["datadog"] = calculate_status_label(non_operational_dd)
        components["datadog"] = datadog_regions_sorted


        # Jira
        jira_components = {}
        try:
            jira_res = await client.get("https://jira-software.status.atlassian.com/api/v2/components.json")
            jira_res.raise_for_status()
            for comp in jira_res.json().get("components", []):
                name = comp.get("name")
                status = comp.get("status")
                jira_components[name] = {
                    "status": status,
                    "severity": status if status.lower() != "operational" else None
                }
        except:
            jira_components = {}

        jira_components_sorted = dict(sorted(
            jira_components.items(),
            key=lambda item: item[1]["status"].lower() == "operational"
        ))

        non_operational_jira = sum(1 for val in jira_components.values() if val["status"].lower() != "operational")
        status_colors["jira"] = calculate_status_color(non_operational_jira)
        details["jira"] = calculate_status_label(non_operational_jira)
        components["jira"] = jira_components_sorted


        # JSM
        jsm_components = {}
        try:
            jsm_res = await client.get("https://jira-service-management.status.atlassian.com/api/v2/components.json")
            jsm_res.raise_for_status()
            for comp in jsm_res.json().get("components", []):
                name = comp.get("name")
                status = comp.get("status")
                jsm_components[name] = {
                    "status": status,
                    "severity": status if status.lower() != "operational" else None
                }
        except:
            jsm_components = {}

        jsm_components_sorted = dict(sorted(
            jsm_components.items(),
            key=lambda item: item[1]["status"].lower() == "operational"
        ))

        non_operational_jsm = sum(1 for val in jsm_components.values() if val["status"].lower() != "operational")
        status_colors["jsm"] = calculate_status_color(non_operational_jsm)
        details["jsm"] = calculate_status_label(non_operational_jsm)
        components["jsm"] = jsm_components_sorted


        # Prisma
        prisma_components = {}
        try:
            prisma_res = await client.get("https://www.prisma-status.com/api/v2/components.json")
            prisma_res.raise_for_status()
            for comp in prisma_res.json().get("components", []):
                name = comp.get("name")
                status = comp.get("status")
                prisma_components[name] = {
                    "status": status,
                    "severity": status if status.lower() != "operational" else None
                }
        except:
            prisma_components = {}

        prisma_components_sorted = dict(sorted(
            prisma_components.items(),
            key=lambda item: item[1]["status"].lower() == "operational"
        ))

        non_operational_prisma = sum(1 for val in prisma_components.values() if val["status"].lower() != "operational")
        status_colors["prisma"] = calculate_status_color(non_operational_prisma)
        details["prisma"] = calculate_status_label(non_operational_prisma)
        components["prisma"] = prisma_components_sorted


        grafana_components = []
        try:
            grafana_res = await client.get("https://status.grafana.com/api/v2/components.json")
            grafana_res.raise_for_status()
            for comp in grafana_res.json().get("components", []):
                name = comp.get("name")
                status = comp.get("status")
                severity = status if status.lower() != "operational" else None
                grafana_components.append({
                    "name": name,
                    "status": status,
                    "severity": severity,
                    "url": f"https://status.grafana.com/components/{comp.get('id')}"
            })
        except Exception as e:
            print(f"Error fetching Grafana components: {e}")
            grafana_components = []

        # Sort non-operational first
        grafana_components_sorted = sorted(
        grafana_components,
        key=lambda c: c["status"].lower() == "operational"
        )

        non_operational_count = sum(1 for c in grafana_components if c["status"].lower() != "operational")
        status_colors["grafana"] = calculate_status_color(non_operational_count)
        details["grafana"] = calculate_status_label(non_operational_count)
        components["grafana"] = grafana_components_sorted


        # Okta
        okta_incidents = {}
        try:
            okta_res = await client.get("https://feeds.feedburner.com/OktaTrustRSS")
            okta_res.raise_for_status()
            root = ET.fromstring(okta_res.text)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else []

            for item in items:
                title = item.find("title").text if item.find("title") is not None else "Unknown"
                if "operational" not in title.lower():
                    okta_incidents[title] = {
                        "status": "non-operational",
                        "severity": "incident"
                    }
        except:
            okta_incidents = {}

        okta_components_sorted = dict(sorted(
            okta_incidents.items(),
            key=lambda item: item[1]["status"] == "operational"
        ))

        non_operational_okta = len(okta_incidents)
        status_colors["okta"] = calculate_status_color(non_operational_okta)
        details["okta"] = "operational" if non_operational_okta == 0 else "degraded"
        components["okta"] = okta_components_sorted


        # Cleverbridge
        cleverbridge_incidents = {}
        try:
            cb_res = await client.get("https://status.cleverbridge.com/history.rss")
            cb_res.raise_for_status()
            root = ET.fromstring(cb_res.text)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else []
            today = datetime.utcnow().strftime('%a, %d %b %Y')
            active = [item for item in items if today in (item.find("pubDate").text or "")]
            if active:
                for item in active:
                    title = item.find("title").text or "Unknown"
                    cleverbridge_incidents[title] = {
                        "status": "non-operational",
                        "severity": "incident"
                    }
            else:
                cleverbridge_incidents = {}
        except Exception:
            cleverbridge_incidents = {}

        cleverbridge_components_sorted = dict(sorted(
            cleverbridge_incidents.items(),
            key=lambda item: item[1]["status"] == "operational"
        ))

        non_operational_cb = len(cleverbridge_incidents)
        status_colors["cleverbridge"] = calculate_status_color(non_operational_cb)
        details["cleverbridge"] = "operational" if non_operational_cb == 0 else "degraded"
        components["cleverbridge"] = cleverbridge_components_sorted

    return templates.TemplateResponse("mainstatus.html", {
        "request": request,
        "details": details,
        "status_colors": status_colors,
        "components": components
    })
