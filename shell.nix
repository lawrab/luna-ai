{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "luna-ai-dev-shell";
  buildInputs = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.zsh 
  ];

  shellHook = ''
    echo "--- Entered L.U.N.A. Development Environment ---"
    # Set up a virtual environment to keep our pip packages isolated
    if [ ! -d ".venv" ]; then
      echo "Creating Python virtual environment..."
      python -m venv .venv
    fi
    source .venv/bin/activate
    pip install --upgrade pip > /dev/null

    # ==> NEW: Install dependencies from requirements.txt <==
    if [ -f "requirements.txt" ]; then
      echo "Installing dependencies from requirements.txt..."
      pip install -r requirements.txt
    fi

    echo "Virtual environment is ready."
  '';
}