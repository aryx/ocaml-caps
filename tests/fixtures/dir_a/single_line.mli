val with_open_in : <Cap.open_in; ..> -> (in_channel -> 'a) -> Fpath.t -> 'a
val system : < Cap.fork; Cap.exec; Cap.wait; .. > -> string -> unit
