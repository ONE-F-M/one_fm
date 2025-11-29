FROM frappe/erpnext:v15.90.1

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























# FROM frappe/erpnext:v15.90.1

# USER root

# # Install openssh-client so we can clone via SSH
# RUN apt-get update && \
#     apt-get install -y openssh-client && \
#     rm -rf /var/lib/apt/lists/*

# USER frappe
# WORKDIR /home/frappe/frappe-bench

# # Create .ssh directory and populate known_hosts for GitHub 
# # (This prevents "Host key verification failed" errors)
# RUN mkdir -p -m 0700 ~/.ssh && \
#     ssh-keyscan github.com >> ~/.ssh/known_hosts && \
#     chmod 600 ~/.ssh/known_hosts


# # --- PRIVATE REPO BLOCK ---
# # 1. We switch the URL to the SSH format (git@github.com:...)
# # 2. We mount the SSH key as a secret named 'ssh_id'
# # 3. We point GIT_SSH_COMMAND to that mounted secret
# RUN --mount=type=secret,id=ssh_id,uid=1000 \
#     GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -i /run/secrets/ssh_id" \
#     bench get-app git@github.com:mymi14s/one_fm.git --branch=version-15 --skip-assets

# # Standard apps can remain on HTTPS if they are public
# RUN bench get-app hrms --branch=version-15 --skip-assets
# RUN bench get-app lending --branch=version-15 --skip-assets
# RUN bench get-app telephony --skip-assets
# RUN bench get-app helpdesk --skip-assets





# # DOCKER_BUILDKIT=1 docker build \
# #   --secret id=ssh_id,src=$HOME/.ssh/id_ed25519 \
# #   -t one-fm:latest .

# # **Key details:**
# # * **`src=$HOME/.ssh/id_rsa`**: This maps your actual local private key to the builder.
# # * **`id=ssh_id`**: This matches the `id=ssh_id` defined in the `RUN --mount` line inside the Dockerfile.
# # * **`DOCKER_BUILDKIT=1`**: Ensures you are using the modern Docker builder that supports secrets (default in newer Docker versions, but good to be explicit).