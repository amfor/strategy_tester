FROM python:3.11

WORKDIR /usr/src/app

RUN apt update \
	&& apt upgrade -y \
	&& apt install -y cmake \
		libjemalloc-dev libboost-dev \
                libboost-filesystem-dev \
                libboost-system-dev \
                libboost-regex-dev \
                autoconf \
                flex \
                bison \
		python3-arrow \
                uv

COPY requirements.txt ./
RUN uv pip install --upgrade pip && pip install pyarrow
RUN uv pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["uv", "run", "streamlit", "run", "./src/strategy_tester.py", "--server.port=8080", "--server.address=0.0.0.0" ]
