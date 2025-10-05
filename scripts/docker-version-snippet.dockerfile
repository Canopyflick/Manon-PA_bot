# Add this to your Dockerfile to include version information
# This should be added before the final CMD instruction

# Generate version information during build
RUN python3 scripts/generate_version.py

# Optional: Set build-time labels with version info
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
LABEL build_date=$BUILD_DATE \
      vcs_ref=$VCS_REF \
      version=$VERSION \
      description="PA Bot with version tracking"