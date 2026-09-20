/**
 * D3 — diagnose the real authorization boundary of the remote WebUI (no browser involved).
 * Answers: which /api routes enforce sessions, what cookie flags the login issues, whether
 * anonymous LAN clients can read or mutate state.
 *
 * Usage: KEL_E2E_PASSWORD=<pw> [KEL_E2E_LAN_IP=a.b.c.d] node packaging/diagnose-remote-auth.cjs
 */
const PORT = Number(process.env.KEL_E2E_PORT || 25901);
const PASSWORD = process.env.KEL_E2E_PASSWORD || '';
const LAN_IP = process.env.KEL_E2E_LAN_IP || '';
const LOCAL = `http://127.0.0.1:${PORT}`;
const LAN = LAN_IP ? `http://${LAN_IP}:${PORT}` : '';

async function probe(label, url, init) {
  const response = await fetch(url, { redirect: 'manual', ...(init || {}) });
  let body = null;
  try {
    body = await response.json();
  } catch {
    /* non-JSON */
  }
  const setCookie = typeof response.headers.getSetCookie === 'function' ? response.headers.getSetCookie() : [];
  return {
    label,
    status: response.status,
    body: body === null ? null : JSON.stringify(body).slice(0, 300),
    setCookie,
  };
}

async function main() {
  const out = { local: LOCAL, lan: LAN || null, results: [] };
  const p = async (label, url, init) => {
    const result = await probe(label, url, init);
    out.results.push(result);
    console.log(JSON.stringify(result));
    return result;
  };

  await p('anon GET /api/conversations (loopback proxy)', `${LOCAL}/api/conversations?page_size=1`);
  await p('anon GET /api/assistants (loopback proxy)', `${LOCAL}/api/assistants`);
  if (LAN) {
    await p('anon GET /api/conversations (LAN)', `${LAN}/api/conversations?page_size=1`);
    await p('anon GET /api/settings/client (LAN)', `${LAN}/api/settings/client`);
  }

  const login = await p('POST /login (correct credentials)', `${LOCAL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: PASSWORD, remember: false }),
  });
  const cookies = login.setCookie.map((entry) => entry.split(';')[0]).join('; ');

  await p('cookie GET /api/conversations', `${LOCAL}/api/conversations?page_size=1`, {
    headers: { cookie: cookies },
  });
  await p('cookie GET /api/auth/user', `${LOCAL}/api/auth/user`, { headers: { cookie: cookies } });
  if (LAN) {
    await p('cookie GET /api/conversations (LAN)', `${LAN}/api/conversations?page_size=1`, {
      headers: { cookie: cookies },
    });
  }

  await p('cookie POST /logout', `${LOCAL}/logout`, { method: 'POST', headers: { cookie: cookies } });
  await p('same cookie GET /api/conversations after logout', `${LOCAL}/api/conversations?page_size=1`, {
    headers: { cookie: cookies },
  });

  if (LAN) {
    const reset = await p('anon POST /api/webui/reset-password (LAN)', `${LAN}/api/webui/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    if (reset.status === 200) {
      console.log('!! anonymous password reset succeeded; new password captured above');
    }
  }

  console.log('\nSUMMARY');
  for (const entry of out.results) {
    console.log(`${String(entry.status).padStart(3)}  ${entry.label}`);
  }
}

main().catch((error) => {
  console.error('diagnose failed:', error);
  process.exit(1);
});
