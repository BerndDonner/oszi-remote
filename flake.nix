{
  description = "Python + Pygame + VSCode + Tabby dev environment";

  inputs = {
    nixos-config.url = "github:BerndDonner/NixOS-Config";
    nixpkgs.follows = "nixos-config/nixpkgs";
  };

  outputs = { self, nixpkgs, nixos-config, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true; # vscode-fhs braucht unfree
        overlays = [
          nixos-config.overlays.unstable
        ];
      };

      pythonDev = nixos-config.lib.mkPythonDevShell;

      python = pkgs.python3.withPackages (ps: [
        ps.pyserial
        ps.matplotlib
        ps.debugpy
        ps.black
        ps.isort
      ]);

    in
    {
      devShells.${system}.default = pythonDev {
        inherit pkgs;
        inputs = { inherit nixos-config nixpkgs; };
        checkInputs = [ "nixos-config" ];
        flakeLockPath = ./flake.lock;
        symbol = "🐍";               # Symbol bleibt gleich
        pythonVersion = python;

        extraPackages = with pkgs; [
          # Für Continue Plugin / VSCode
          vscode-fhs
        ];

        message = "🐍 VSCode (FHS) + Python (pyserial, matplotlib) dev shell ready";
      };
    };
}

