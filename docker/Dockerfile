# Builds an image for a container that runs the Reibun crawler.

FROM friedrice2/reibun/base

ENV REIBUN_SRC_DIR $REIBUN_BASE_DIR/src

ENV REIBUN_DEV_CONFIG_DIR $REIBUN_BASE_DIR/devconf
ENV IPYTHONDIR $REIBUN_DEV_CONFIG_DIR/ipython
VOLUME ["$REIBUN_DEV_CONFIG_DIR"]

# Install requirements before copying any source files. This way the cached result
# of this fairly time-consuming step can be used during image builds even if
# any of the source files change.
COPY ./requirements.txt $REIBUN_SRC_DIR/
RUN python3.7 -m pip install -r $REIBUN_SRC_DIR/requirements.txt

# Copy full source files directory
COPY . $REIBUN_SRC_DIR

ENV REIBUN_LOG_DIR $REIBUN_BASE_DIR/log
VOLUME ["$REIBUN_LOG_DIR"]

WORKDIR $REIBUN_SRC_DIR

ENTRYPOINT ["ipython"]
