# Changelog

## [1.9.1](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.9.0...NavimowHA-v1.9.1) (2026-10-12)


### Bug Fixes

* **navimow:** prevent stale MQTT cache from replacing newer state ([eb85d4d](https://github.com/geert36/NavimowHA/commit/eb85d4d2b034faa99931a41b63e3487485745834))

## [1.9.0](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.8.0...NavimowHA-v1.9.0) (2026-10-12)


### Features

* more setting switches and battery-threshold number entities ([ce3496f](https://github.com/geert36/NavimowHA/commit/ce3496fb745ebd5b51b125161bd1cfb823747b3f))

## [1.8.0](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.7.0...NavimowHA-v1.8.0) (2026-10-12)


### Features

* controllable mower settings as switches (private cloud) ([6d85fed](https://github.com/geert36/NavimowHA/commit/6d85fed10f96ace77c43f9e131b92247b9883eb6))
* **switch:** optimistic state and faster pro polling ([af8d288](https://github.com/geert36/NavimowHA/commit/af8d288a33de6f9a543f1a00c69b8cd40680eb2a))

## [1.7.0](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.6.0...NavimowHA-v1.7.0) (2026-10-11)


### Features

* expose mower settings as binary sensors and number sensors ([0c0726c](https://github.com/geert36/NavimowHA/commit/0c0726c4bcfca4421ed5dbfc814c68cfa205210c))

## [1.6.0](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.5.0...NavimowHA-v1.6.0) (2026-10-10)


### Features

* **config_flow:** add/update app login via Options (reconfigure) ([027dcc8](https://github.com/geert36/NavimowHA/commit/027dcc88e5ef4272f2b41445978bdb231fb1b80a))
* **config_flow:** optional private-cloud app login step ([144aeea](https://github.com/geert36/NavimowHA/commit/144aeea4616122c19166b31f2ffe95a8ba8f0040))
* **sensor:** add Wi-Fi signal and settings sensors via private cloud ([a95f081](https://github.com/geert36/NavimowHA/commit/a95f0815a8d6501671449cb670c110656577e6f9))
* **sensor:** blade and chassis service-life sensors via private cloud ([837c088](https://github.com/geert36/NavimowHA/commit/837c088fbdecb24f6fa90044f99afafd2f0bb804))

## [1.5.0](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.4.1...NavimowHA-v1.5.0) (2026-10-09)


### Features

* **sensor:** make sensor names translatable and add Dutch ([a0aad76](https://github.com/geert36/NavimowHA/commit/a0aad760b415a268633c3929377b029c57daa5bb))

## [1.4.1](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.4.0...NavimowHA-v1.4.1) (2026-10-09)


### Features

* **sensor:** map operating_mode to readable labels ([a72aa82](https://github.com/geert36/NavimowHA/commit/a72aa82b09073ecd206e2c75f184c6b0531e6d39))


### Miscellaneous Chores

* release 1.4.1 ([d986b94](https://github.com/geert36/NavimowHA/commit/d986b94c80c66cd9b5883c8f02a693770787f4c2))

## [1.4.0](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.3.0...NavimowHA-v1.4.0) (2026-10-09)


### Features

* **sensor:** retain last value for mowing-session sensors ([3eb9eff](https://github.com/geert36/NavimowHA/commit/3eb9eff966c3ad1768b3a767e3d58d0abfe4279c))

## [1.3.0](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.2.8...NavimowHA-v1.3.0) (2026-10-09)


### Features

* **sensor:** expand vehicleState label catalog ([7290667](https://github.com/geert36/NavimowHA/commit/72906674a9e9e048bbcd24526f827bb2570c2daf))

## [1.2.8](https://github.com/geert36/NavimowHA/compare/NavimowHA-v1.2.7...NavimowHA-v1.2.8) (2026-10-09)


### Features

* add danish translation ([2de5eab](https://github.com/geert36/NavimowHA/commit/2de5eab0679b68bafc66cb61eff33f3de37c568d))
* Add french translation ([303d3c8](https://github.com/geert36/NavimowHA/commit/303d3c8187c48636ac23aec293dfcbd9300fc744))


### Bug Fixes

* **navimow:** Fix OAuth token expiration issue after MQTT disconnection ([26c8ed5](https://github.com/geert36/NavimowHA/commit/26c8ed5bd7853afdb00c61ad27e2344ca8794e3e))
* **navimow:** Fixed MQTT credential refresh and unload logic ([7381489](https://github.com/geert36/NavimowHA/commit/738148937b92e659ee9c000a1308db5e389ebf22))
* **navimow:** improve MQTT reconnection handling and entity availability ([c04ae31](https://github.com/geert36/NavimowHA/commit/c04ae312f0685705215b8cfc31c1400d6c96a5e0))
* **navimow:** Optimize re-authentication error handling, distinguishing between deterministic and transient failures ([cb2bd56](https://github.com/geert36/NavimowHA/commit/cb2bd56eea8be91a8cded3e76dd74c5a5a68301e))
* **navimow:** Optimizes MQTT connection keepalive and reconnection mechanisms ([0f38417](https://github.com/geert36/NavimowHA/commit/0f384173283644e1a93798993e4152eaeb7f40b3))
* **navimow:** recover faster from silent MQTT outages and stale state ([6ddacc3](https://github.com/geert36/NavimowHA/commit/6ddacc324b8b6228f9d02d092722e8ffbd72e168))
* **navimow:** treat MQTT user info circuit-breaker as non-fatal ([964ea60](https://github.com/geert36/NavimowHA/commit/964ea6011fa50c15464ad1f21eacdfcc608ce758)), closes [#49](https://github.com/geert36/NavimowHA/issues/49)


### Miscellaneous Chores

* align release-please baseline and release 1.2.8 ([d45d0b2](https://github.com/geert36/NavimowHA/commit/d45d0b2a07c3c9e34bfe5dc281559e993589f366))

## [1.1.0](https://github.com/segwaynavimow/NavimowHA/compare/NavimowHA-v1.0.0...NavimowHA-v1.1.0) (2026-04-10)


### Features

* add danish translation ([2de5eab](https://github.com/segwaynavimow/NavimowHA/commit/2de5eab0679b68bafc66cb61eff33f3de37c568d))
* Add french translation ([303d3c8](https://github.com/segwaynavimow/NavimowHA/commit/303d3c8187c48636ac23aec293dfcbd9300fc744))


### Bug Fixes

* **navimow:** Fix OAuth token expiration issue after MQTT disconnection ([26c8ed5](https://github.com/segwaynavimow/NavimowHA/commit/26c8ed5bd7853afdb00c61ad27e2344ca8794e3e))
* **navimow:** Fixed MQTT credential refresh and unload logic ([7381489](https://github.com/segwaynavimow/NavimowHA/commit/738148937b92e659ee9c000a1308db5e389ebf22))
* **navimow:** improve MQTT reconnection handling and entity availability ([c04ae31](https://github.com/segwaynavimow/NavimowHA/commit/c04ae312f0685705215b8cfc31c1400d6c96a5e0))
* **navimow:** Optimize re-authentication error handling, distinguishing between deterministic and transient failures ([cb2bd56](https://github.com/segwaynavimow/NavimowHA/commit/cb2bd56eea8be91a8cded3e76dd74c5a5a68301e))
* **navimow:** Optimizes MQTT connection keepalive and reconnection mechanisms ([0f38417](https://github.com/segwaynavimow/NavimowHA/commit/0f384173283644e1a93798993e4152eaeb7f40b3))

## Changelog

所有版本变更将由自动化发布流程生成。
