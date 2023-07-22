package com.example.cj

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import com.example.cj.databinding.ActivityConveyorMainBinding

class ConveyorMain : AppCompatActivity() {
    private var mBinding: ActivityConveyorMainBinding? = null
    //매번 null 체크하지 않도록 확인 후 재 선언
    private val binding get() = mBinding!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        //setContentView(R.layout.activity_conveyor_main)

        mBinding = ActivityConveyorMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val intent = Intent(this,StopboxMain::class.java)
        binding.backbtn.setOnClickListener {startActivity(intent)}
    }
}