use std::io::Write;
use std::path::PathBuf;
use std::{env, fs, io};

fn main() -> io::Result<()> {
    let output =
        PathBuf::from(env::var_os("OUT_DIR").ok_or_else(|| io::Error::other("OUT_DIR missing"))?);
    for file in ["memory.x", "image-end.x"] {
        fs::copy(file, output.join(file))?;
        writeln!(io::stdout(), "cargo:rerun-if-changed={file}")?;
    }
    writeln!(io::stdout(), "cargo:rustc-link-search={}", output.display())?;
    Ok(())
}
