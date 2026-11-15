import { useEffect, useState, type RefObject } from 'react';

type State = 'idle' | 'copied' | 'selected';

/** Copies `text`: through the clipboard if the browser allows it, else
 *  through a hidden field and the older copy command. False if neither did. */
async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // refused: some in-app browsers block the clipboard; try the field
  }
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  // 16px keeps a phone from zooming to the field
  field.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;font-size:16px';
  document.body.appendChild(field);
  field.select();
  field.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand('copy');
  } catch {
    ok = false;
  }
  field.remove();
  return ok;
}

/**
 * A labeled copy button. When the browser refuses every way of copying, it
 * selects `select` (the text on the page) so the reader can copy it with the
 * device's own Copy, and says so.
 */
export default function CopyButton(props: {
  text: string;
  label: string;
  className?: string;
  select?: RefObject<HTMLElement | null>;
}) {
  const [state, setState] = useState<State>('idle');

  useEffect(() => setState('idle'), [props.text]);
  useEffect(() => {
    if (state === 'idle') return;
    const t = window.setTimeout(() => setState('idle'), 4000);
    return () => window.clearTimeout(t);
  }, [state]);

  const onClick = async () => {
    if (await copyText(props.text)) {
      setState('copied');
      return;
    }
    const el = props.select?.current;
    if (el) {
      const range = document.createRange();
      range.selectNodeContents(el);
      const s = window.getSelection();
      s?.removeAllRanges();
      s?.addRange(range);
    }
    setState('selected');
  };

  return (
    <>
      <button type="button" className={props.className} onClick={onClick}>
        {state === 'copied' ? 'Copied' : props.label}
      </button>
      <span className="visually-hidden" role="status">
        {state === 'copied' ? 'Copied.' : ''}
      </span>
      {state === 'selected' && (
        <span className="copy-fallback" role="status">
          {props.select ? 'This browser blocks copying. The text is selected: use your device’s Copy.' : 'This browser blocks copying.'}
        </span>
      )}
    </>
  );
}
