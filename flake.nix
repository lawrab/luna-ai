{
  description = "L.U.N.A. AI Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: {
    devShells.x86_64-linux.default = let
      pkgs = import nixpkgs { system = "x86_64-linux"; };
    in
      pkgs.mkShell {
        name = "luna-ai-dev-shell";
        buildInputs = [
          pkgs.python311
          pkgs.python311Packages.pip
          pkgs.zsh
          pkgs.libnotify # For notify-send
        ];

        shell = pkgs.zsh; # Ensure zsh is the shell

        shellHook = ''
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
          exec zsh
        '';
      };
  };
}