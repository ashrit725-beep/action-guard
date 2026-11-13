import { useEffect, useState } from "react";

import { api } from "@/lib/api";

// Whether the in-app helper can answer: the server has a working Anthropic key.
// Asked once per page load and shared by everything that mentions the helper, so
// nobody is pointed at a button that is not there.
let pending = null;

export function useAssistantAvailable() {
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    let alive = true;
    pending =
      pending ||
      api
        .get("/assistant/status")
        .then(({ data }) => Boolean(data?.available))
        .catch(() => {
          pending = null; // try again next time rather than remembering a failure
          return false;
        });
    pending.then((value) => {
      if (alive) setAvailable(value);
    });
    return () => {
      alive = false;
    };
  }, []);

  return available;
}
