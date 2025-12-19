#!/bin/bash
# Build Lambda layer and function zip files for S3 upload
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/layers" "$BUILD_DIR/lambdas"

# Build browser-deps layer
echo "Building browser-deps layer..."
LAYER_DIR="$BUILD_DIR/layer-tmp/python"
mkdir -p "$LAYER_DIR"
pip install boto3 playwright bedrock-agentcore -t "$LAYER_DIR" --quiet --upgrade
cd "$BUILD_DIR/layer-tmp"
zip -r "$BUILD_DIR/layers/browser-deps.zip" python -q
cd "$SCRIPT_DIR"
rm -rf "$BUILD_DIR/layer-tmp"

# Build start_viewing Lambda
echo "Building start_viewing Lambda..."
cd "$SCRIPT_DIR/lambdas"
zip "$BUILD_DIR/lambdas/start_viewing.zip" start_viewing.py
cd "$SCRIPT_DIR"

echo "Build complete. Upload to S3:"
echo "  aws s3 cp $BUILD_DIR/layers/browser-deps.zip s3://\${BUCKET}/layers/"
echo "  aws s3 cp $BUILD_DIR/lambdas/start_viewing.zip s3://\${BUCKET}/lambdas/"
