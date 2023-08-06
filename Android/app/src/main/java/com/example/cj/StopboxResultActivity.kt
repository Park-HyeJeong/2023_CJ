package com.example.cj

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import com.example.cj.databinding.ActivityConveyorMainBinding
import com.example.cj.databinding.ActivityStopboxResultBinding

class StopboxResultActivity : AppCompatActivity() {
    private var mBinding: ActivityStopboxResultBinding? = null
    //매번 null 체크하지 않도록 확인 후 재 선언
    private val binding get() = mBinding!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        //setContentView(R.layout.activity_conveyor_main)

        mBinding = ActivityStopboxResultBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val intent = Intent(this,MainActivity::class.java)

        binding.homebtn.setOnClickListener { startActivity(intent) }
    }
}