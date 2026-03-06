/*
Drill 01 — File Storage

Implement a FileStorage class that manages files in memory.
Each level adds new methods. Keep all previous methods working.

────────────────────────────────────────
Level 1 — Basic Operations

  addFile(name: string, size: number): boolean
    Add a file. Returns true if added, false if name already exists.

  getFileSize(name: string): number
    Returns the file's size, or -1 if not found.

  deleteFile(name: string): boolean
    Removes the file. Returns true if deleted, false if not found.

────────────────────────────────────────
Level 2 — Copy & Search

  copyFile(source: string, dest: string): boolean
    Copy source to dest (overwrites dest if it exists).
    Returns false if source does not exist.

  search(prefix: string): string[]
    Returns up to 10 file names that start with prefix.
    Sort by size descending, then name ascending for ties.

────────────────────────────────────────
Level 3 — Capacity

  Constructor accepts an optional capacity (max total bytes).
  No capacity means unlimited storage.

  addFile returns false if adding would exceed capacity.
  copyFile returns false if copying would exceed capacity
    (only counts the net change — overwriting a file replaces its size).

  getUsedSpace(): number — total bytes stored
  getRemainingSpace(): number — bytes remaining (Infinity if unlimited)

────────────────────────────────────────
Level 4 — Undo

  undo(): boolean
    Reverts the last successful add, delete, or copy.
    Returns false if there is nothing to undo.
    Multiple undo() calls walk back through history.
*/

export class FileStorage {
  constructor(capacity?: number) {
    // TODO: initialize your data structures
  }

  addFile(name: string, size: number): boolean {
    throw new Error("TODO: implement addFile");
  }

  getFileSize(name: string): number {
    throw new Error("TODO: implement getFileSize");
  }

  deleteFile(name: string): boolean {
    throw new Error("TODO: implement deleteFile");
  }

  copyFile(source: string, dest: string): boolean {
    throw new Error("TODO: implement copyFile");
  }

  search(prefix: string): string[] {
    throw new Error("TODO: implement search");
  }

  getUsedSpace(): number {
    throw new Error("TODO: implement getUsedSpace");
  }

  getRemainingSpace(): number {
    throw new Error("TODO: implement getRemainingSpace");
  }

  undo(): boolean {
    throw new Error("TODO: implement undo");
  }
}

// ─── Self-Checks (do not edit below this line) ──────────────────

function check(label: string, actual: unknown, expected: unknown): void {
  if (Object.is(actual, expected)) return;
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a === e) return;
  throw new Error(`${label}: expected ${e}, got ${a}`);
}

function runSelfChecks(): void {
  // ── Level 1 ──
  const s1 = new FileStorage();
  check("L1 add new", s1.addFile("a.txt", 100), true);
  check("L1 add dup", s1.addFile("a.txt", 999), false);
  check("L1 get exists", s1.getFileSize("a.txt"), 100);
  check("L1 get missing", s1.getFileSize("z.txt"), -1);
  check("L1 delete exists", s1.deleteFile("a.txt"), true);
  check("L1 delete missing", s1.deleteFile("a.txt"), false);
  check("L1 get after delete", s1.getFileSize("a.txt"), -1);

  // ── Level 2 ──
  const s2 = new FileStorage();
  s2.addFile("app.js", 300);
  s2.addFile("api.js", 300);
  s2.addFile("assets.zip", 100);
  s2.addFile("readme.md", 50);
  check("L2 copy ok", s2.copyFile("app.js", "app_backup.js"), true);
  check("L2 copy missing", s2.copyFile("nope.txt", "x.txt"), false);
  check("L2 search", s2.search("a"),
    ["api.js", "app.js", "app_backup.js", "assets.zip"]);
  check("L2 search no match", s2.search("zzz"), []);

  // ── Level 3 ──
  const s3 = new FileStorage(500);
  check("L3 add within", s3.addFile("a.txt", 200), true);
  check("L3 add within 2", s3.addFile("b.txt", 200), true);
  check("L3 add exceeds", s3.addFile("c.txt", 200), false);
  check("L3 used", s3.getUsedSpace(), 400);
  check("L3 remaining", s3.getRemainingSpace(), 100);
  const s3b = new FileStorage();
  s3b.addFile("x.txt", 1000);
  check("L3 no limit remaining", s3b.getRemainingSpace(), Infinity);

  // ── Level 4 ──
  const s4 = new FileStorage();
  s4.addFile("file.txt", 100);
  s4.deleteFile("file.txt");
  check("L4 after delete", s4.getFileSize("file.txt"), -1);
  check("L4 undo delete", s4.undo(), true);
  check("L4 restored", s4.getFileSize("file.txt"), 100);
  check("L4 undo add", s4.undo(), true);
  check("L4 fully undone", s4.getFileSize("file.txt"), -1);
  check("L4 nothing left", s4.undo(), false);

  const s4b = new FileStorage();
  s4b.addFile("src.txt", 200);
  s4b.copyFile("src.txt", "dst.txt");
  check("L4 copy created", s4b.getFileSize("dst.txt"), 200);
  check("L4 undo copy", s4b.undo(), true);
  check("L4 copy undone", s4b.getFileSize("dst.txt"), -1);
  check("L4 src intact", s4b.getFileSize("src.txt"), 200);
}

function main(): void {
  try {
    runSelfChecks();
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    if (msg.startsWith("TODO:")) {
      console.log(msg);
      return;
    }
    console.log(`FAIL: ${msg}`);
    return;
  }
  console.log("All self-checks passed.");
}

main();
