FROM grafana/grafana:latest

ENV GF_SECURITY_ADMIN_PASSWORD=admin

COPY ./grafana/provisioning /etc/grafana/provisioning
COPY ./grafana/dashboards /var/lib/grafana/dashboards

EXPOSE 3000