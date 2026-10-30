use serde_json::{Value, json};

pub(crate) fn report(rate: f64, periods: u32) -> u64 {
    let text = format!(
        r#"{{"rate":{rate},"years":{periods},"assets":[{{"value":10000.0,"coupon":250.0}},{{"value":3500.0,"coupon":75.0}},{{"value":8100.0,"coupon":180.0}}]}}"#
    );
    let Ok(input) = serde_json::from_str::<Value>(&text) else {
        return 0;
    };
    let Some(assets) = input["assets"].as_array() else {
        return 0;
    };
    let mut output = Vec::new();
    for asset in assets {
        let Some(principal) = asset["value"].as_f64() else {
            return 0;
        };
        let Some(coupon) = asset["coupon"].as_f64() else {
            return 0;
        };
        let mut pv = 0.0;
        let mut duration = 0.0;
        let mut continuous_pv = 0.0;
        let mut path = Vec::new();
        for year in 1..=periods.min(120) {
            let t = f64::from(year);
            let discount = libm::pow(1.0 + rate, -t);
            let payment = coupon + if year == periods { principal } else { 0.0 };
            let cash = payment * discount;
            pv += cash;
            duration += t * cash;
            continuous_pv += payment * libm::exp(-rate * t);
            let half_life_weight = libm::exp2(-t / 10.0);
            path.push(json!({"year":year,"present_value":cash,"discount":discount,
                             "ten_year_half_life_weight":half_life_weight}));
        }
        output.push(json!({"present_value":pv,"duration":duration/pv,
                           "continuous_present_value":continuous_pv,"cashflows":path}));
    }
    let Ok(encoded) = serde_json::to_vec(&json!({"assets":output,"rate":rate})) else {
        return 0;
    };
    encoded.iter().fold(0xcbf29ce484222325u64, |hash, byte| {
        (hash ^ u64::from(*byte)).wrapping_mul(0x100000001b3)
    })
}
