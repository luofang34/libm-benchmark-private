use std::io::Write;
use std::path::PathBuf;
use std::{env, fs, io};

fn main() -> io::Result<()> {
    let output =
        PathBuf::from(env::var_os("OUT_DIR").ok_or_else(|| io::Error::other("OUT_DIR missing"))?);
    fs::copy("memory.x", output.join("memory.x"))?;
    writeln!(io::stdout(), "cargo:rerun-if-changed=memory.x")?;
    writeln!(io::stdout(), "cargo:rustc-link-search={}", output.display())?;
    Ok(())
}
