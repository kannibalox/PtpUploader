# Serves a source of truth for third-party JS/CSS, primarily to avoid
# having to rely on javascript tooling.
set -euo pipefail
wget https://raw.githubusercontent.com/necolas/normalize.css/8.0.1/normalize.css -O normalize.css
pushd script
wget https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.contextMenu.min.js -O jquery.contextMenu.min.js
wget https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.ui.position.min.js -O jquery.ui.position.min.js
wget https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.2/css/bulma.min.css -O bulma.min.css
wget https://cdn.datatables.net/v/bm/dt-1.11.3/datatables.min.css -O datatables.min.css
wget https://cdn.datatables.net/v/bm/dt-1.11.3/datatables.min.js -O datatables.min.js
wget https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/js/all.min.js -O fontawesome.all.min.js

wget https://cdn.jsdelivr.net/npm/jquery.fancytree@2.27/dist/skin-win8/ui.fancytree.min.css -O ui.fancytree.min.css
wget https://cdn.jsdelivr.net/npm/jquery.fancytree@2.27/dist/jquery.fancytree-all-deps.min.js -O jquery.fancytree-all-deps.min.js
wget https://code.jquery.com/ui/1.12.1/jquery-ui.min.js -O jquery-ui.min.js
wget https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css -O jquery-confirm.min.css
wget https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.js -O jquery-confirm.min.js
wget https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css -O select2.min.css
wget https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js -O select2.min.js
popd
