open! Core
open Hardcaml_workbench_protocol

let version = 1
let max_stdout_bytes = 1024 * 1024
let describe_capability = "describe"
let generate_rtl_capability = "generate-rtl"
let max_outputs = 16

module Clock = struct
  type t =
    { name : string
    ; period_ns : float option
    ; description : string option
    }
  [@@deriving compare, equal, sexp]
end

module Fact = struct
  type t =
    { namespace : string
    ; name : string
    ; value : string
    ; display : string option
    }
  [@@deriving compare, equal, sexp]
end

module Target = struct
  type t =
    { key : string
    ; name : string
    ; top : string
    ; backend : string
    ; clocks : Clock.t list
    ; facts : Fact.t list
    }
  [@@deriving compare, equal, sexp]
end

module Configuration = struct
  type t =
    { key : string
    ; target : string
    ; name : string
    ; description : string option
    }
  [@@deriving compare, equal, sexp]
end

module Describe_response = struct
  type t =
    { protocol_version : int
    ; capabilities : string list
    ; targets : Target.t list
    ; configurations : Configuration.t list
    }
  [@@deriving compare, equal, sexp]
end

module Tool = struct
  type t =
    { name : string
    ; version : string option
    }
  [@@deriving compare, equal, sexp]
end

module Backend_ref = struct
  type t =
    { backend : string
    ; id : string
    ; label : string option
    }
  [@@deriving compare, equal, sexp]
end

module Run_ref = struct
  type t =
    { backend : string
    ; id : string
    ; build : Backend_ref.t option
    ; label : string option
    }
  [@@deriving compare, equal, sexp]
end

module Output = struct
  type t =
    { path : string
    ; namespace : string
    ; name : string
    ; role : Artifact.Role.t
    ; media : string option
    ; display_name : string
    ; description : string option
    }
  [@@deriving compare, equal, sexp]
end

module Generate_rtl_response = struct
  type t =
    { protocol_version : int
    ; target : string
    ; configuration : string
    ; outputs : Output.t list
    ; tools : Tool.t list
    ; build : Backend_ref.t option
    ; run : Run_ref.t option
    }
  [@@deriving compare, equal, sexp]
end

let valid_key value =
  let valid_tail = function
    | 'A' .. 'Z' | 'a' .. 'z' | '0' .. '9' | '.' | '_' | '-' -> true
    | _ -> false
  in
  match String.to_list value with
  | ('A' .. 'Z' | 'a' .. 'z' | '0' .. '9') :: tail -> List.for_all tail ~f:valid_tail
  | [] | _ -> false
;;

let nonempty field value =
  if String.is_empty value then Error (field ^ " must not be empty") else Ok ()
;;

let unique_keys kind values ~key =
  let seen = Hash_set.create (module String) in
  List.fold_result values ~init:() ~f:(fun () value ->
    let value = key value in
    if not (valid_key value)
    then Error (sprintf "%s key %S is invalid" kind value)
    else if Hash_set.mem seen value
    then Error (sprintf "%s key %S is duplicated" kind value)
    else (
      Hash_set.add seen value;
      Ok ()))
;;

let validate (response : Describe_response.t) =
  if response.protocol_version <> version
  then
    Error
      (sprintf
         "unsupported driver protocol version %d (supported: 1)"
         response.protocol_version)
  else if not (List.mem response.capabilities describe_capability ~equal:String.equal)
  then Error "driver does not advertise required capability describe"
  else (
    let%bind.Result () =
      unique_keys "target" response.targets ~key:(fun target -> target.key)
    in
    let%bind.Result () =
      unique_keys "configuration" response.configurations ~key:(fun config -> config.key)
    in
    let target_keys =
      String.Set.of_list (List.map response.targets ~f:(fun target -> target.key))
    in
    let%bind.Result () =
      List.fold_result response.targets ~init:() ~f:(fun () target ->
        let%bind.Result () = nonempty "target.name" target.name in
        let%bind.Result () = nonempty "target.top" target.top in
        let%bind.Result () = nonempty "target.backend" target.backend in
        Ok ())
    in
    let%map.Result () =
      List.fold_result response.configurations ~init:() ~f:(fun () config ->
        let%bind.Result () = nonempty "configuration.name" config.name in
        if Set.mem target_keys config.target
        then Ok ()
        else
          Error
            (sprintf
               "configuration %S refers to unknown target key %S"
               config.key
               config.target))
    in
    response)
;;

let parse output =
  if String.length output > max_stdout_bytes
  then Error (sprintf "driver stdout exceeded %d bytes" max_stdout_bytes)
  else (
    match
      Or_error.try_with (fun () -> Sexp.of_string output |> Describe_response.t_of_sexp)
    with
    | Error error ->
      Error ("malformed driver describe response: " ^ Error.to_string_hum error)
    | Ok response -> validate response)
;;

let valid_relative_path path =
  (not (String.is_empty path))
  && not (Filename.is_absolute path)
  && (String.split path ~on:'/'
      |> List.for_all ~f:(fun component ->
        not
          (String.is_empty component
           || String.equal component "."
           || String.equal component "..")))
;;

let validate_backend_ref field (reference : Backend_ref.t) =
  let%bind.Result () = nonempty (field ^ ".backend") reference.backend in
  nonempty (field ^ ".id") reference.id
;;

let validate_generate ~target ~configuration (response : Generate_rtl_response.t) =
  if response.protocol_version <> version
  then
    Error
      (sprintf
         "unsupported driver protocol version %d (supported: 1)"
         response.protocol_version)
  else if not (String.equal response.target target)
  then Error "generate-rtl result target does not match the request"
  else if not (String.equal response.configuration configuration)
  then Error "generate-rtl result configuration does not match the request"
  else if List.is_empty response.outputs
  then Error "generate-rtl result declared no outputs"
  else if List.length response.outputs > max_outputs
  then Error (sprintf "generate-rtl result exceeded %d outputs" max_outputs)
  else (
    let seen = Hash_set.create (module String) in
    let%bind.Result () =
      List.fold_result response.outputs ~init:() ~f:(fun () output ->
        if not (valid_relative_path output.path)
        then Error (sprintf "output path %S is not a normalized relative path" output.path)
        else if Hash_set.mem seen output.path
        then Error (sprintf "output path %S is duplicated" output.path)
        else (
          Hash_set.add seen output.path;
          let%bind.Result () = nonempty "output.namespace" output.namespace in
          let%bind.Result () = nonempty "output.name" output.name in
          nonempty "output.display_name" output.display_name))
    in
    let%bind.Result () =
      List.fold_result response.tools ~init:() ~f:(fun () tool ->
        nonempty "tool.name" tool.name)
    in
    let%bind.Result () =
      Option.value_map response.build ~default:(Ok ()) ~f:(validate_backend_ref "build")
    in
    let%map.Result () =
      Option.value_map response.run ~default:(Ok ()) ~f:(fun run ->
        let%bind.Result () = nonempty "run.backend" run.backend in
        let%bind.Result () = nonempty "run.id" run.id in
        Option.value_map run.build ~default:(Ok ()) ~f:(validate_backend_ref "run.build"))
    in
    response)
;;

let parse_generate ~target ~configuration output =
  if String.length output > max_stdout_bytes
  then Error (sprintf "driver stdout exceeded %d bytes" max_stdout_bytes)
  else (
    match
      Or_error.try_with (fun () ->
        Sexp.of_string output |> Generate_rtl_response.t_of_sexp)
    with
    | Error error ->
      Error ("malformed driver generate-rtl response: " ^ Error.to_string_hum error)
    | Ok response -> validate_generate ~target ~configuration response)
;;
