FROM --platform=linux/x86_64 sweb.env.py.x86_64.e5bb89bf78258a7d14c34b:latest

COPY ./setup_repo.sh /root/
RUN sed -i -e 's/\r$//' /root/setup_repo.sh
RUN /bin/bash /root/setup_repo.sh

WORKDIR /testbed/
