FROM frappe/erpnext:v15.90.1

USER root

RUN apt-get update && rm -rf /var/lib/apt/lists/*

USER frappe
WORKDIR /home/frappe/frappe-bench

RUN bench get-app hrms --branch=version-15 --skip-assets
RUN bench get-app lending --branch=version-15 --skip-assets
RUN bench get-app telephony --skip-assets
RUN bench get-app helpdesk --skip-assets
RUN bench get-app https://github.com/mymi14s/one_fm --branch=version-15 --skip-assets
