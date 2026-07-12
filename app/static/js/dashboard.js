(function () {
  const board = document.getElementById("board");
  if (!board) return;

  // ---------- Drag and drop (Interact.js) ----------
  function saveCardPosition(cardEl) {
    const id = cardEl.dataset.id;
    const x = parseInt(cardEl.dataset.x, 10) || 0;
    const y = parseInt(cardEl.dataset.y, 10) || 0;

    fetch(`/api/servicos/${id}/posicao`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pos_x: x, pos_y: y }),
    }).catch(() => {
      // Falha silenciosa: a posição será re-sincronizada no próximo drag ou reload
    });
  }

  interact(".card").draggable({
    inertia: false,
    modifiers: [
      interact.modifiers.restrictRect({
        restriction: "parent",
        endOnly: true,
      }),
    ],
    listeners: {
      move(event) {
        const target = event.target;
        const x = (parseFloat(target.dataset.x) || 0) + event.dx;
        const y = (parseFloat(target.dataset.y) || 0) + event.dy;

        target.style.transform = `translate(${x}px, ${y}px)`;
        target.dataset.x = x;
        target.dataset.y = y;
      },
      end(event) {
        saveCardPosition(event.target);
      },
    },
  });

  // ---------- Polling de status em tempo real ----------
  const POLL_INTERVAL_MS = 5000;
  const subtitle = document.getElementById("board-subtitle");
  const onlineList = document.getElementById("online-list");
  const onlineCount = document.getElementById("online-count");

  function renderOnlineList(list) {
    if (!onlineList) return;

    const onlineServices = list.filter((svc) => svc.status === "verde");

    if (onlineCount) onlineCount.textContent = onlineServices.length;

    if (onlineServices.length === 0) {
      onlineList.innerHTML = '<li class="online-empty">Nenhum serviço online no momento.</li>';
      return;
    }

    onlineList.innerHTML = onlineServices
      .map((svc) => {
        const ping = svc.ping !== null ? `${svc.ping} ms` : "—";
        return `<li class="online-item" data-id="${svc.id}">
          <span class="online-ball"></span>
          <span class="online-name">${svc.nome}</span>
          <span class="online-ping">${ping}</span>
        </li>`;
      })
      .join("");
  }

  function applyStatus(list) {
    let online = 0;

    list.forEach((svc) => {
      const card = board.querySelector(`.card[data-id="${svc.id}"]`);
      if (!card) return;

      card.classList.remove("status-verde", "status-amarelo", "status-vermelho", "status-cinza");
      card.classList.add(`status-${svc.status}`);
      if (svc.status === "verde") online += 1;

      const pingEl = card.querySelector(".card-ping");
      if (pingEl) pingEl.textContent = svc.ping !== null ? `${svc.ping} ms` : "—";

      const checkEl = card.querySelector(".card-check");
      if (checkEl && svc.ultima_verificacao) {
        const timePart = svc.ultima_verificacao.split(" ")[1] || svc.ultima_verificacao;
        checkEl.textContent = timePart;
      }
    });

    renderOnlineList(list);

    if (subtitle) {
      subtitle.textContent = `${online} de ${list.length} serviço${list.length !== 1 ? "s" : ""} online`;
    }
  }

  async function pollStatus() {
    try {
      const resp = await fetch("/api/status", { headers: { Accept: "application/json" } });
      if (!resp.ok) return;
      const data = await resp.json();
      applyStatus(data);
    } catch (err) {
      // Rede indisponível momentaneamente: tenta novamente no próximo ciclo
    }
  }

  pollStatus();
  setInterval(pollStatus, POLL_INTERVAL_MS);
})();
