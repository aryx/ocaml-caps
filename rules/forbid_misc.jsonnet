local common = import 'common.libsonnet';

{
  rules: [
    {
      id: 'forbid-random',
      match: { any: [
        'Random.$F',
      ] },
      languages: ['ocaml'],
      paths: common.exclude,
      severity: 'ERROR',
      message: |||
        Do not use directly Random; use the safer CapRandom module.
      |||,
    },
    {
      id: 'forbid-clock',
      match: { any: [
        'Unix.gettimeofday',
        'Unix.time',
        'Unix.sleepf',
        'Unix.sleep',
        'Sys.time',
      ] },
      languages: ['ocaml'],
      paths: common.exclude,
      severity: 'ERROR',
      message: |||
        Do not use directly the clock; use CapUnix's or CapSys's
        functions, which take Cap.clock.
      |||,
    },
    {
      id: 'forbid-obj-magic',
      match: { any: [
        'Obj.magic',
      ] },
      languages: ['ocaml'],
      paths: {
        exclude: [
         ],
      },
      severity: 'ERROR',
      message: |||
        Do not use Obj.magic. Period.
      |||,
    },
  ],

}
