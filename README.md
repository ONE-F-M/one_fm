## One Fm

<p align="center">
  <img src="https://img.shields.io/badge/Frappe-15-blue?style=for-the-badge&logo=frappe">
  <img src="https://img.shields.io/badge/ERPNext-15-green?style=for-the-badge&logo=erpnext">
  <br/>
</p>

## Overview
One Facilities Management is a leader in the fields of commercial automation and integrated security management systems providing the latest products and services in these fields. This repository contains the code for a customized app built on top of ERPNext. ERPNext is a free and open-source integrated Enterprise Resource Planning software developed by Frappé Technologies Pvt. Ltd. and is built on MariaDB database system using a Python based server-side framework. ERPNext is a generic ERP software used by manufacturers, distributors and services companies.

## [Live Demo](https://dev.one-fm.com/)

## Getting started


### Core Requirements
Before you install this app, ensure that the following apps and their respective versions are installed:

- Frappe Framework: 15 (version-15)
- ERPNext: v15 (version-15)
- Helpdesk: v15 or main (main)
- Frappe HR: v15 (version-15)
- One Fm Password Management: v0.0.1 (master)
- Wiki: v15 (master-15)
- Payments: v15 (version-16)
- Twilio Integration: (master)

#### Requirements

- Python 3.10 or above
- MariaDB 10.6 or above
- Node V18
- Redis


### Package installation
Execute the following command on your terminal in the frapp-bench directory to get and install OneFm app
``` bash
bench get-app https://github.com/ONE-F-M/One-FM.git
bench install-app one_fm
```
Once the installation is done we need to run
``` bash
bench update
```
For these and other major changes to take effect.

#### License

MIT# One-FM
