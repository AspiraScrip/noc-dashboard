(function () {
  const board = document.getElementById("board");
  if (!board) return;

  // ---------- Conexões (linhas entre cards) ----------
  const svgLayer = document.getElementById("connections-layer");
  const connectBtn = document.getElementById("connect-mode-btn");
  const connectHint = document.getElementById("connect-hint");

  let connections = [];
  const connDataEl = document.getElementById("connections-data");
  if (connDataEl) {
    try {
      connections = JSON.parse(connDataEl.textContent);
    } catch (e) {
      connections = [];
    }
  }

  let connectMode = false;
  let selectedOrigin = null;

  function clearSelection() {
    if (selectedOrigin) {
      selectedOrigin.classList.remove("connect-selected");
    }
    selectedOrigin = null;
  }

  if (connectBtn) {
    connectBtn.addEventListener("click", () => {
      connectMode = !connectMode;
      connectBtn.classList.toggle("active", connectMode);
      board.classList.toggle("connect-mode", connectMode);
      if (connectHint) connectHint.hidden = !connectMode;
      clearSelection();
    });
  }

  async function criarConexao(origemId, destinoId) {
    try {
      const resp = await fetch("/api/conexoes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          origem_id: Number(origemId),
          destino_id: Number(destinoId)
        })
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        alert(data.erro || "Não foi possível criar a conexão.");
        return;
      }
      connections.push(data.conexao);
      renderConnections();
    } catch (e) {
      alert("Erro ao conectar ao servidor.");
    }
  }

  async function excluirConexao(id) {
    if (!confirm("Remover esta conexão?")) return;
    try {
      const resp = await fetch(`/api/conexoes/${id}`, { method: "DELETE" });
      if (!resp.ok) return;
      connections = connections.filter(c => c.id !== id);
      renderConnections();
    } catch (e) {
    }
  }

  function cardCenter(card) {
    const x = parseFloat(card.dataset.x) || 0;
    const y = parseFloat(card.dataset.y) || 0;
    return {
      x: x + card.offsetWidth / 2,
      y: y + card.offsetHeight / 2
    };
  }

  function connectionColor(statusA, statusB) {
    if (!statusA || !statusB || statusA === "vermelho" || statusB === "vermelho") {
      return "vermelho";
    }
    if (statusA === "amarelo" || statusB === "amarelo") {
      return "amarelo";
    }
    if (statusA === "verde" && statusB === "verde") {
      return "verde";
    }
    return "cinza";
  }

  function resizeSvgLayer() {
    if (!svgLayer) return;
    const w = Math.max(board.scrollWidth, board.clientWidth, 1);
    const h = Math.max(board.scrollHeight, board.clientHeight, 1);
    svgLayer.setAttribute("width", w);
    svgLayer.setAttribute("height", h);
    svgLayer.setAttribute("viewBox", `0 0 ${w} ${h}`);
  }

  function renderConnections() {
    if (!svgLayer) return;
    resizeSvgLayer();
    svgLayer.innerHTML = "";

    connections.forEach(conn => {
      const origemCard = board.querySelector(`.card[data-id="${conn.origem_id}"]`);
      const destinoCard = board.querySelector(`.card[data-id="${conn.destino_id}"]`);
      if (!origemCard || !destinoCard) return;

      const p1 = cardCenter(origemCard);
      const p2 = cardCenter(destinoCard);
      const color = connectionColor(origemCard.dataset.status, destinoCard.dataset.status);

      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.classList.add("connection-line");

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", p1.x);
      line.setAttribute("y1", p1.y);
      line.setAttribute("x2", p2.x);
      line.setAttribute("y2", p2.y);
      line.classList.add("connection-path", `conn-${color}`);

      const hit = document.createElementNS("http://www.w3.org/2000/svg", "line");
      hit.setAttribute("x1", p1.x);
      hit.setAttribute("y1", p1.y);
      hit.setAttribute("x2", p2.x);
      hit.setAttribute("y2", p2.y);
      hit.classList.add("connection-hit");
      hit.addEventListener("click", () => excluirConexao(conn.id));

      group.appendChild(line);
      group.appendChild(hit);
      svgLayer.appendChild(group);
    });
  }

  window.addEventListener("resize", renderConnections);

  if (window.interact) {
    interact(".card").on("tap", event => {
      if (!connectMode) return;
      const card = event.currentTarget;

      if (!selectedOrigin) {
        selectedOrigin = card;
        card.classList.add("connect-selected");
        return;
      }
      if (selectedOrigin === card) {
        clearSelection();
        return;
      }
      const origemId = selectedOrigin.dataset.id;
      const destinoId = card.dataset.id;
      clearSelection();
      criarConexao(origemId, destinoId);
    });
  }

  // ---------- Drag and drop ----------
  function saveCardPosition(cardEl) {
    const id = cardEl.dataset.id;
    const x = parseInt(cardEl.dataset.x, 10) || 0;
    const y = parseInt(cardEl.dataset.y, 10) || 0;
    fetch(`/api/servicos/${id}/posicao`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        pos_x: x,
        pos_y: y
      })
    });
  }
  interact(".card").draggable({
    inertia: false,
    modifiers: [
      interact.modifiers.restrictRect({
        restriction: "parent",
        endOnly: true
      })
    ],
    listeners: {
      move(event) {
        const target = event.target;
        const x =
          (parseFloat(target.dataset.x) || 0)
          + event.dx;
        const y =
          (parseFloat(target.dataset.y) || 0)
          + event.dy;
        target.style.transform =
          `translate(${x}px, ${y}px)`;
        target.dataset.x = x;
        target.dataset.y = y;
        renderConnections();
      },
      end(event) {
        saveCardPosition(event.target);
        renderConnections();
      }
    }
  });
  // ---------- STATUS EM TEMPO REAL ----------
  const POLL_INTERVAL_MS = 10000;
  const subtitle =
    document.getElementById("board-subtitle");
  const onlineList =
    document.getElementById("online-list");
  const offlineList =
    document.getElementById("offline-list");
  const onlineCount =
    document.getElementById("online-count");
  const offlineCount =
    document.getElementById("offline-count");
  function renderSidebars(list) {
    const online =
      list.filter(
        s => s.status === "verde"
      );
    const offline =
      list.filter(
        s => s.status === "vermelho"
      );
    // ONLINE
    if (onlineList) {
      if (online.length === 0) {
        onlineList.innerHTML =
          `
        <li class="online-empty">
        Nenhum serviço online no momento.
        </li>
        `;
      }
      else {
        onlineList.innerHTML =
          online.map(s => `
        <li class="online-item"
            data-id="${s.id}">
          <span class="online-ball"></span>
          <span class="online-name">
            ${s.nome}
          </span>
          <span class="online-ping">
            ${s.ping !== null ? s.ping + " ms" : "—"}
          </span>
        </li>
        `).join("");
      }
    }
    // OFFLINE
    if (offlineList) {
      if (offline.length === 0) {
        offlineList.innerHTML =
          `
        <li class="offline-empty">
        Nenhum serviço offline no momento.
        </li>
        `;
      }
      else {
        offlineList.innerHTML =
          offline.map(s => `
        <li class="offline-item"
            data-id="${s.id}">
          <span class="offline-ball"></span>
          <span class="offline-name">
            ${s.nome}
          </span>
          <span class="offline-ping">
            ${s.ping !== null ? s.ping + " ms" : "—"}
          </span>
        </li>
        `).join("");
      }
    }
    if (onlineCount)
      onlineCount.textContent = online.length;
    if (offlineCount)
      offlineCount.textContent = offline.length;
  }
  function applyStatus(list) {
    let online = 0;
    list.forEach(svc => {
      const card =
        board.querySelector(
          `.card[data-id="${svc.id}"]`
        );
      if (!card) return;
      card.classList.remove(
        "status-verde",
        "status-amarelo",
        "status-vermelho",
        "status-cinza"
      );
      card.classList.add(
        `status-${svc.status}`
      );
      card.dataset.status = svc.status;
      if (svc.status === "verde")
        online++;
      const ping =
        card.querySelector(".card-ping");
      if (ping) {
        ping.textContent =
          svc.ping !== null
            ? `${svc.ping} ms`
            : "—";
      }
      const check =
        card.querySelector(".card-check");
      if (check && svc.ultima_verificacao) {
        const hora =
          svc.ultima_verificacao.split(" ")[1]
          ||
          svc.ultima_verificacao;
        check.textContent = hora;
      }
    });
    renderSidebars(list);
    if (subtitle) {
      subtitle.textContent =
        `${online} de ${list.length} serviço${list.length !== 1 ? "s" : ""} online`;
    }
  }
  async function pollStatus() {
    try {
      const resp =
        await fetch(
          "/api/status",
          {
            headers: {
              Accept: "application/json"
            }
          }
        );
      if (!resp.ok) return;
      const data =
        await resp.json();
      applyStatus(data.services || []);
      connections = data.connections || connections;
      renderConnections();
    }
    catch (e) {
    }
  }
  renderConnections();
  pollStatus();
  setInterval(
    pollStatus,
    POLL_INTERVAL_MS
  );
})();