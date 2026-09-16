{
  description = "Web development project";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      flake-utils,
      nixpkgs,
    }@inputs:

    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [

            # Typescript
            typescript
            typescript-language-server
            vtsls

            # NodeJS
            nodejs

            # Tools
            biome

          ];

          shellHook = ''
            node --version
          '';
        };

      }
    );

}
