{ pkgs }: {
  deps = [
    pkgs.python311Full
    pkgs.python311Packages.telethon
    pkgs.python311Packages.aiohttp
    pkgs.python311Packages.flask
  ];
}
