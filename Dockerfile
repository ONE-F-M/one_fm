FROM frappe/erpnext:v15.90.1

ENV PIP_NO_CACHE_DIR=1

USER root

RUN apt-get update && rm -rf /var/lib/apt/lists/*

USER frappe
WORKDIR /home/frappe/frappe-bench

RUN bench get-app hrms --branch=version-15 --skip-assets && rm -rf apps/hrms/.git
RUN bench get-app lending --branch=version-15 --skip-assets && rm -rf apps/lending/.git
RUN bench get-app telephony --skip-assets && rm -rf apps/telephony/.git
RUN bench get-app helpdesk --skip-assets && rm -rf apps/helpdesk/.git
RUN bench get-app https://${GITHUB_TOKEN}@github.com/mymi14s/one_fm --branch=version-15 --skip-assets && \
    rm -rf apps/one_fm/.git
