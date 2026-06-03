FROM grafana/grafana:latest

ENV GF_SECURITY_ADMIN_PASSWORD=admin

# Comentario de test
COPY ./provisioning /etc/grafana/provisioning/
COPY ./dashboards /var/lib/grafana/dashboards/

EXPOSE 3000