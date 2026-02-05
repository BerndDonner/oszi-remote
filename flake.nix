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

      pythonDev = import (nixos-config + "/lib/python-develop.nix");
    in
    {
      devShells.${system}.default = pythonDev {
        inherit pkgs;
        inputs = { inherit nixos-config nixpkgs; };
        checkInputs = [ "nixos-config" ];
        flakeLockPath = ./flake.lock;
        symbol = "🐍";               # Symbol bleibt gleich
        pythonVersion = pkgs.python3;

        extraPackages = with pkgs; [
          # Messtechnik / Oszi
          python3Packages.pyserial
          python3Packages.matplotlib

          # Dev-Qualität (optional, aber nützlich)
          python3Packages.debugpy
          python3Packages.black
          python3Packages.isort

          # Für Continue Plugin / VSCode
          vscode-fhs
        ];

        message = "🐍 VSCode (FHS) + Python (pyserial, matplotlib) dev shell ready";
      };
    };
}

