#!/bin/sh
set -e

cat <<EOF > /usr/share/nginx/html/env.js
window._env_ = {
    VITE_BACKEND_HOST: "${VITE_BACKEND_HOST}",
    VITE_BACKEND_PORT: "${VITE_BACKEND_PORT}",
};
EOF

echo "Env injected"
cat /usr/share/nginx/html/env.js

exec nginx -g 'daemon off;'