FROM python:3.11

WORKDIR /app
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
		python3-arrow  \ 
                curl \ 
                ca-certificates

ENV PATH="/root/.local/bin/:$PATH"
ADD https://astral.sh/uv/0.5.9/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app

ENTRYPOINT []
CMD ["uv", "run", "streamlit", "run", "./src/strategy_tester.py", "--server.port=8080", "--server.address=0.0.0.0" ]