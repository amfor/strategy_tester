FROM python:3.8

WORKDIR /usr/src/app

RUN apt update \
	&& apt upgrade -y \
	&& apt install -y cmake \
		libjemalloc-dev libboost-dev \
                libboost-filesystem-dev \
                libboost-system-dev \
                libboost-regex-dev \
                python-dev \
                autoconf \
                flex \
                bison \
		python3-arrow

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install pyarrow
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT [ "streamlit", "run", "./src/strategy_tester.py", "--server.port=8080', '--server.address=0.0.0.0' ]
