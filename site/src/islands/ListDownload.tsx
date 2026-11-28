import layoutFile from '../../../pipeline/research/release/layout_v1.0.json';
import { VERSION } from '../lib/codegen';
import type { Cube, Selection } from '../lib/cube';
import { DEFAULT_TITLE, buildSheet, sheetMarkdown, type SheetMeta } from '../lib/datasheet';
import { plannedBytes, type Layout } from '../lib/list-read';
import { LIST_SOURCE } from '../lib/release-state';
import ZipDownload from './ZipDownload';

const layout = layoutFile as Layout;

/** The list's text in bytes, 1 string and a line break per row, from the
 *  lengths in characters; the top bucket counts as its least length, and a
 *  character outside ASCII takes more than 1 byte, so it is an estimate. */
function textBytes(cube: Cube, sel: Selection): number {
  return cube.byLength(sel, true).reduce((n, rows, i) => n + rows * (i + 2), 0);
}

/**
 * "Download the list" on Compose a list: reads the list from the dataset's
 * universe file in the reader's browser and saves it as a zip with its
 * datasheet and notices. While the dataset is private it says it opens with
 * the release.
 */
export default function ListDownload(props: {
  cube: Cube;
  sel: Selection;
  rows: number;
  query: string;
  citation: string;
  file: SheetMeta['file'];
}) {
  const { cube, sel, rows, query } = props;
  const files = async (signal: AbortSignal) => {
    let notices: string;
    try {
      const res = await fetch(`/data/NOTICES-${VERSION}.md`, { signal });
      if (!res.ok) throw new Error(String(res.status));
      notices = await res.text();
    } catch {
      throw new Error('The notices that travel with the list did not load.');
    }
    const meta: SheetMeta = {
      title: DEFAULT_TITLE,
      author: '',
      note: '',
      made: new Date(),
      link: `${window.location.origin}/compose/${query}`,
      citation: props.citation,
      file: props.file,
    };
    return [
      { name: 'DATASHEET.md', text: sheetMarkdown(buildSheet(sel, cube), meta) },
      { name: 'NOTICES.md', text: notices },
    ];
  };
  return (
    <ZipDownload
      source={LIST_SOURCE}
      closedNote={
        <>
          Opens with the public release of version {VERSION.slice(1)}. Until then, the code below reproduces the list, and
          you can download a list from <a href="/compose/open/">the open subset</a> now.
        </>
      }
      layout={layout}
      filter={{ of: 'universe', sel, lengthCap: cube.lengthCap }}
      rows={rows}
      listKey={query}
      zipName={`ceol-universe-${VERSION}-${rows}-rows.zip`}
      textBytes={textBytes(cube, sel)}
      readBytes={plannedBytes(layout, sel, cube.lengthCap)}
      fileLabel="the dataset's file"
      files={files}
    />
  );
}
