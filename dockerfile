FROM mikewootini/wget
RUN apt-get update && apt-get upgrade -y && apt-get install -y tsocks
ADD http://10.101.228.11:8000/file/tsocks.conf /etc/tsocks.conf
RUN "/bin/sh"
