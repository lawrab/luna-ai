{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "luna-ai-dev-shell";
  buildInputs = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.zsh
    pkgs.libnotify # <== ADD THIS for notify-send
  ];

  shellHook = ''
    # ... shellHook remains the same
    echo "--- Entered L.U.N.A. Development Environment ---"
    if [ ! -d ".venv" ]; then
      echo "Creating Python virtual environment..."
      python -m venv .venv
    fi
    source .venv/bin/activate
    pip install --upgrade pip > /dev/null
    if [ -f "requirements.txt" ]; then
      echo "Installing dependencies from requirements.txt..."
      pip install -r requirements.txt
    fi
    echo "Virtual environment is ready. Zsh and notify-send are available."
  '';
}