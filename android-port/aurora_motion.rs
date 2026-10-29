
// Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
// Twenty distinct procedural skeletal gestures, independent of upstream clips.
pub(crate) fn evaluate_aurora(id: u8, t: f32) -> AnimFrame {
    let mut f = AnimFrame::rest();
    let s = (t * 4.0).sin();
    let pulse = (t * std::f32::consts::PI / 3.2).sin().max(0.0);
    match id {
        0 => { f.arms[1].z = 2.3 + s * 0.35; f.arms[1].x = -0.25; },
        1 => f.head_rot.x = s * 0.4,
        2 => f.head_rot.y = (t*2.0).sin()*0.8,
        3 => { f.body_rot.x = -0.65*pulse; f.head_rot.x = -0.2*pulse; },
        4 => { f.arms[0].z = -2.7*pulse; f.arms[1].z = 2.7*pulse; },
        5 => { f.arms[0].z = -1.6*pulse; f.arms[1].z = 1.6*pulse; f.head_rot.x=0.3*pulse; },
        6 => { f.body_rot.z = s*0.18; f.arms[0].z=-0.3; f.arms[1].z=0.3; },
        7 => { f.legs[0].x=s*0.65; f.legs[1].x=-s*0.65; f.arms[0].x=-s*0.5; f.arms[1].x=s*0.5; },
        8 => { f.legs[0].x=s*0.95; f.legs[1].x=-s*0.95; f.arms[0].x=-s*1.0; f.arms[1].x=s*1.0; f.body_rot.x=-0.25; },
        9 => { f.body_pos.y=(1.0-(t*8.0).cos())*1.25; f.arms[0].z=-0.5; f.arms[1].z=0.5; },
        10 => { f.body_rot.y=s*0.4; f.arms[0].z=-1.1+s*0.4; f.arms[1].z=1.1+s*0.4; f.legs[0].z=-0.1;f.legs[1].z=0.1; },
        11 => { f.arms[1].x=-1.6*pulse; f.arms[1].z=0.6*pulse; f.head_rot.x=-0.1; },
        12 => { f.head_rot.z=0.2*pulse; f.arms[1].x=-1.2*pulse; f.arms[1].z=0.25*pulse; },
        13 => { f.arms[0].x=-1.1; f.arms[1].x=-1.1; f.arms[0].y=s*0.45;f.arms[1].y=-s*0.45; },
        14 => { f.arms[0].z=-1.4; f.arms[1].z=1.4; f.legs[0].x=0.5*pulse; f.body_rot.z=-0.15*pulse; },
        15 => { f.body_rot.z=-0.32*pulse; f.head_rot.z=0.2*pulse; f.arms[1].z=0.55*pulse; },
        16 => { f.arms[0].x=s*0.6; f.arms[0].z=-0.4; f.arms[1].x=(t*4.0+1.57).sin()*0.6;f.arms[1].z=0.4; },
        17 => { f.head_rot.x=0.65*pulse; f.head_rot.y=0.3*s; },
        18 => { f.legs[1].x=-0.95*pulse; f.arms[0].x=-0.5*pulse; f.arms[1].x=0.5*pulse; },
        _ => { f.arms[0].z=-2.4;f.arms[1].z=2.4;f.body_pos.y=(1.0-(t*8.0).cos())*0.75;f.body_rot.y=s*0.25; },
    }
    // Smoothstep envelope has zero endpoint velocity: no pose snap at start/end.
    let ease = |x: f32| { let x=x.clamp(0.0,1.0); x*x*(3.0-2.0*x) };
    let weight=ease(t/0.28)*ease((3.2-t)/0.4);
    f.body_rot*=weight; f.head_rot*=weight; f.body_pos*=weight;
    for joint in f.arms.iter_mut().chain(f.legs.iter_mut()) { *joint*=weight; }
    f
}

#[cfg(test)] mod aurora_tests {
 use super::*;
 #[test] fn twenty_distinct_finite_poses() {
  let mut keys=std::collections::HashSet::new();
  for id in 0..20 {
   let f=evaluate_aurora(id,0.7);
   assert!(f.body_rot.is_finite() && f.head_rot.is_finite() && f.body_pos.is_finite());
   assert!(f.arms.iter().chain(f.legs.iter()).all(|v|v.is_finite()));
   let values=[f.body_rot,f.head_rot,f.arms[0],f.arms[1],f.legs[0],f.legs[1],f.body_pos];
   let key:Vec<_>=values.iter().flat_map(|v|v.to_array().map(|x|x.to_bits())).collect();
   assert!(keys.insert(key),"duplicate gesture {id}");
  }
 }
}


#[cfg(test)] mod aurora_smoothing_tests {
 use super::*;
 #[test] fn gesture_endpoints_are_at_rest() {
  for id in 0..20 { for t in [0.0,3.2,3.3] {
   let f=evaluate_aurora(id,t);
   assert!(f.body_rot.length()<1e-6 && f.head_rot.length()<1e-6 && f.body_pos.length()<1e-6);
   assert!(f.arms.iter().chain(f.legs.iter()).all(|v|v.length()<1e-6));
  }}
 }
 #[test] fn all_gestures_are_continuous() {
  for id in 0..20 { for tick in 0..320 {
   let a=evaluate_aurora(id,tick as f32/100.0);let b=evaluate_aurora(id,(tick+1) as f32/100.0);
   assert!((a.body_pos-b.body_pos).length()<0.2);
   assert!(a.arms.iter().zip(b.arms.iter()).all(|(x,y)|(*x-*y).length()<0.2));
  }}
 }
}
