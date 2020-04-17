![Alt text](http://kalenislims.com/img/isologo-kalenis.png)

---

[![Alt text](https://drone.kalenislims.com/api/badges/kalenis/kalenislims/status.svg)](https://drone.kalenislims.com/kalenis/kalenislims)

[Kalenis LIMS](http://kalenislims.com/) is an open source solution designed in an integral way with the aim of supporting all laboratory processes, prioritizing the integrity, traceability and accessibility of information. It provides a complete solution for Food, Beverages and Environment industries, in full compliance with standards [ISO 17025](http://en.wikipedia.org/wiki/ISO/IEC_17025) and [GLP](http://en.wikipedia.org/wiki/Good_laboratory_practice).

## Getting Started

These instructions will get you a copy of the project up and running.

### Installing

Execute:

    pip install kalenis-lims


Once installed you have to setup the server with this command:

```
kalenis-cli setup -l <language> -i <industry>
```

To run the server execute:

```
kalenis-cli run
```

## Built With

* [Tryton](http://www.tryton.org/)

## License

See LICENSE file in each module

## Copyright

See COPYRIGHT file in each module
