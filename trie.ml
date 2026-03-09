type trie = {
  mutable last_used: int;
  mutable freq: int;
  mutable children: (char * trie) list;
  mutable terminal: bool;
}

let nb_mot_saisie = ref 0

let create_trie () = 
  { last_used = 0;
    freq = 0;
    children = [];
    terminal = false
  }

let add t word = 
  let size = String.length word in
  let rec add_node i t = 
    if (i = size) then t.terminal <- true
    else 
      t.children <- add_list i t.children

  and add_list i l = 
    match l with
    [] -> 
      let new_trie = create_trie () in (*factoriser code ?*)
      add_node (i+1) new_trie;
      (word.[i], new_trie)::[]
    |(ck, tk) :: ll -> 
      let ci = word.[i] in 
      if ci < ck then 
        let new_trie = create_trie () in (*factoriser code ?*)
        add_node (i+1) new_trie;
        (word.[i], new_trie)::l
      else if ci > ck then
        (ck,tk)::add_list i ll
      else 
        (
        add_node (i+1) tk;
        (ck,tk)::ll)
   in add_node 0 t
