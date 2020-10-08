# Send Control Command

curl -i -X POST 192.168.1.111:8087/set/sysControl/state/requestState "Content-Type: application/json" --data-binary '{"data" : "STANDBY"}'



## License

Licensed under either of

* Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
* MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.