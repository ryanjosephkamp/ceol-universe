/**
 * Whether the dataset is public yet, and where the list download reads it.
 *
 * Until the release, the dataset on the Hugging Face hub is private: the
 * generated code needs access, and the list download cannot read it, so its
 * button says it opens with the release. At the release, set DATASET_PUBLIC
 * to true (site/README.md, "The list download").
 *
 * For a local test before then, `PUBLIC_LIST_SOURCE` names a copy of the
 * universe file served with range requests; it opens the button against that
 * copy, in a dev build only.
 */

import { DATASET, VERSION } from './codegen';

export const DATASET_PUBLIC = false;

/** The universe file of the version on the hub, at the version's tag. */
export const HUB_LIST_SOURCE = `https://huggingface.co/datasets/${DATASET}/resolve/${VERSION}/data/universe.parquet`;

const localSource: string | undefined = import.meta.env.DEV ? import.meta.env.PUBLIC_LIST_SOURCE : undefined;

/** Where the download reads the file, or null while it cannot. */
export const LIST_SOURCE: string | null = localSource || (DATASET_PUBLIC ? HUB_LIST_SOURCE : null);
